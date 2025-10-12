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
    ret = await db.exec("SELECT current FROM version", ())
    if not ret:
        current_ver = 0
    else:
        current_ver = int(ret['current'])
    return current_ver

async def _set_db_version(db, old, new):
    logger = logging.getLogger("versioning")
    if "--test-versioning" in sys.argv:
        logger.debug("In test mode, not recording database version change!")
        return True
    try:
        if old == 0:
            await db.exec("INSERT INTO version VALUES(%s)", (new, ))
        else:
            await db.exec("UPDATE version SET current=%s WHERE current=%s", (new, old))
    except:
        logging.getLogger("versioning").debug(traceback.format_exc())
    return True

def _show_db_version_advice(current_db_version, highest_db_version):
    """Show info about the database state and the action the versioning system will take."""
    logger = logging.getLogger("versioning")
    logger.warning(f"The current database version is {current_db_version}.")
    if current_db_version < highest_db_version:
        logger.warning(f"Your database is out of date. The highest available version is {highest_db_version}.")
        logger.warning("Updating to this version.")
    elif current_db_version == highest_db_version:
        logger.warning(f"The database is up to date, nothing to do at the moment.")
        return True
    elif current_db_version > highest_db_version:
        logger.error("The current database version is higher than what is available! You may experience issues with data storage.")
        if not "--allow-rollback" in sys.argv:
            logger.warning("To attempt to roll back changes, run Maximilian with --allow-rollback")
            logger.warning("This will cause data loss. See HOSTING.md for details.")
            return True
        else:
            logger.warning("Database rollback enabled.")

async def eval_db_version(db):
    """Check database version and update if necessary."""
    logger = logging.getLogger("versioning")
    logger.debug("Checking database version.")
    try:
        versions = _load_db_version_file()
    except:
        logger.debug(traceback.format_exc())
        return logger.error("Unable to load database version listing!")
    version_nums = sorted(list(versions.keys()))
    logger.debug(f"Available database versions are {version_nums[-1]} - {version_nums[0]}")
    current_db_version = await _get_current_db_version(db)
    ret = _show_db_version_advice(current_db_version, version_nums[0])
    if ret:
        return
    for num in version_nums:
        if not num > current_db_version:
            logger.debug(f"Skipping version {num}")
            continue
        logger.debug(f"Applying database patch for version {num}: {versions[num][0]}")
        logger.debug(f"Command(s) to run: {versions[num][1]}")
        if "--test-versioning" in sys.argv:
            logger.debug("In testing mode, not applying database changes!")
            continue
        if ";" in versions[num][1]:
            cmds = versions[num][1].split(";")
        else:
            cmds = [versions[num][1]]
        try:
            for cmd in cmds:
                await db.exec(cmd)
        except:
            logger.warning("Database patch for version {num} failed!")
            logger.warning("You may experience issues. Please report this to tk___421.")
            traceback.print_exc()
            return
        logger.debug("Patch applied.")
    ret = await _set_db_version(db, current_db_version, num)
    if not ret:
        logger.warning("The database update could not be recorded!")
        logger.warning("This could cause issues in the future. Consider reporting this to tk___421.")
    else:
        logger.warning("Database update complete.")
    

