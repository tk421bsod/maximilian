"""Provides facilities for database version upgrades."""

import logging
import sys
import traceback

def _load_db_version_file():
    versions = {}
    with open("db_versions", "r") as versionfile:
        contents = versionfile.readlines()
        for line in contents:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            ver, desc, cmds, rb_cmds = line.split(":")
            versions[int(ver)] = [desc, cmds, rb_cmds]
    return versions

async def _get_current_db_version(db):
    logger = logging.getLogger('versioning')
    ret = None
    try:
        ret = await db.exec("SELECT * FROM version ORDER BY num DESC", ())
        logger.debug(ret)
    except:
        logger.debug(traceback.format_exc())
        pass
    if not ret:
        current_ver = 0
    else:
        current_ver = int(ret[0]['num'])
    return current_ver

async def _set_db_version(db, new, rb_cmds):
    logger = logging.getLogger("versioning")
    if "--test-versioning" in sys.argv:
        logger.debug("In test mode, not recording database version change!")
        return
    await db.exec("INSERT INTO version VALUES(%s, %s)", (new, rb_cmds))

def _show_db_version_advice(current_db_version, highest_db_version):
    """Show info about the database state and the action the versioning system will take."""
    logger = logging.getLogger("versioning")
    logger.warning(f"The current database version is {current_db_version}.")
    if current_db_version < highest_db_version:
        logger.warning(f"Your database is out of date. The highest available version is {highest_db_version}.")
        logger.warning("Updating to this version.")
    elif current_db_version == highest_db_version:
        logger.warning(f"The database is up to date, nothing to do at the moment.")
        return 0
    elif current_db_version > highest_db_version:
        logger.error("The current database version is higher than what is available! You may experience issues with data storage.")
        if not "--allow-rollback" in sys.argv:
            logger.error("To attempt to roll back changes, run Maximilian with --allow-rollback.")
            logger.error("This will cause data loss. See HOSTING.md for details.")
            return 0
        else:
            logger.warning("Database rollback enabled.")
            return 1
    return 2

async def _do_database_rollback(db, current_db_version, version_nums):
    logger = logging.getLogger('versioning')
    for num in range(current_db_version, version_nums[-1], -1): #Descending from current version to highest available version.
        logger.debug(f"Beginning rollback for version {num}.")
        ret = await db.exec("SELECT rollback_commands FROM version WHERE num = %s", (num))
        ret = ret[0]
        if ret['rollback_commands'] == 'None':
            logger.debug(f"Rollback intentionally excluded for this database change. Skipping.")
            continue
        logger.debug(f"Obtained rollback command set: '{ret['rollback_commands']}'")
        try:
            for rollback_cmd in ret['rollback_commands'].split(';'):
                await db.exec(rollback_cmd, ())
            await db.exec("DELETE FROM version WHERE num=%s", (num, ))
        except:
            logger.error(f"Rollback for database version {num} failed! The rollback process cannot continue.")
            logger.error("You may experience issues, please report this error.")
            traceback.print_exc()
            return
    logger.warning("Database rollback completed.")

def _check_error_type(e):
    COLUMN_ALREADY_EXISTS_ERRORNO = 1060
    from pymysql import OperationalError
    if isinstance(e, OperationalError):
        if e.args[0] == COLUMN_ALREADY_EXISTS_ERRORNO:
            logging.getLogger('versioning').debug("Column already exists, ignoring.")
            return True #We can safely continue (maybe the patch was already applied? or the table was just created with the utd schema)

async def _do_database_update(db, current_db_version, version_nums, available_versions):
    """Perform a database update by applying database patches in ascending order."""
    logger = logging.getLogger('versioning')
    for num in version_nums:
        if not num > current_db_version:
            logger.debug(f"Skipping version {num}")
            continue
        logger.debug(f"Applying database patch for version {num}: {available_versions[num][0]}")
        logger.debug(f"Command(s) to run: {available_versions[num][1]}")
        if ";" in available_versions[num][1]:
            cmds = available_versions[num][1].split(";")
        else:
            cmds = [available_versions[num][1]]
        if "--test-versioning" in sys.argv:
            logger.debug("In testing mode, not applying database changes!")
            continue
        try:
            for cmd in cmds:
                await db.exec(cmd, ())
        except Exception as e:
            if not _check_error_type(e):
                logger.error("Database patch for version {num} failed! The database update cannot continue.")
                logger.error("You may experience issues. Please report this to tk___421.")
                traceback.print_exc()
                return
        try:
            #Record this database patch
            await _set_db_version(db, num, available_versions[num][2])
        except:
            logger.error(f"Database patch for version {num} could not be recorded! The database update cannot continue.")
            logger.error("You may experience issues. Please report this to tk___421.")
            return
        logger.debug("Patch applied.")
    logger.warning("Database update completed.")

async def eval_db_version(db):
    """Check database version and update if necessary."""
    logger = logging.getLogger("versioning")
    logger.debug("Checking database version.")
    try:
        available_versions = _load_db_version_file()
    except:
        logger.debug(traceback.format_exc())
        return logger.error("Unable to load database version listing!")
    logger.debug(available_versions)
    version_nums = sorted(list(available_versions.keys()))
    logger.debug(f"Available database versions are {version_nums[0]} - {version_nums[-1]}")
    current_db_version = await _get_current_db_version(db)
    action = _show_db_version_advice(current_db_version, version_nums[-1])
    if action == 0: #No action needed.
        import time; time.sleep(2)
        return
    elif action == 1: #Database rollback needed.
        new_version = await _do_database_rollback(db, current_db_version, version_nums)
    elif action == 2: #Database update needed.
        new_version = await _do_database_update(db, current_db_version, version_nums, available_versions)

if __name__ == "__main__":
    from common import show_not_executable
    show_not_executable()
