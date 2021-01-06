from aiohttp import web
import datetime
import pymysql
import pymysql.cursors
import os
from common import db

dbinst = db()
try:
    dbinst.connect("maximilian")
except pymyql.err.OperationalError:
    print("Couldn't connect to database. Check the database configuration.")
    quit()

routes = web.RouteTableDef()

@routes.get('/other-projects/maximilian/api')
async def save(request):
    try:
        print("Request recieved")
        values = {}
        #TODO: Use the 'logging' module for logging, as it simplifies this
        print("getting parameters...")
        valuenodupe = request.rel_url.query.get('valuenodupe', '')
        table = request.rel_url.query.get('table', '')
        path = request.rel_url.query.get('path', '')
        database = request.rel_url.query.get('database', '')
        debug = bool(request.rel_url.query.get('debug', False))
        valueallnum = request.rel_url.query.get('valueallnum', '')
        valueallnumenabled = bool(request.rel_url.query.get('valueallnumenabled', 'false'))
        currentdomain = request.rel_url.query.get('currentdomain', 'animationdoctorstudio.net')
        print("appending values to dict of values")
        for key, value in request.rel_url.query.items():
            if value != valuenodupe and value != table and value != path and value != debug and value != database and value != valueallnum and value != str(valueallnumenabled) and value != currentdomain:
                values[key] = value
        print(currentdomain)
        if debug == True:
            print(valuenodupe)
            print(str(values))
            print(table)
            print(path)
            print(debug)
        path = path.replace("/", "")
        if "responses" in path:
            result = dbinst.insert(database, table, values, valuenodupe, debug, valueallnum, valueallnumenabled, "guild_id", True)
        else:
            result = dbinst.insert(database, table, values, valuenodupe, debug, valueallnum, valueallnumenabled, "", False)
        results = {"success":"?redirectsource=savechanges&changessaved=success", "debuginfoprinted":"", "error-duplicate":"?redirectsource=savechanges&changessaved=error-duplicate", "error-unhandled":"?redirectsource=savechanges&changessaved=error-other&error="+dbinst.error+"&errorlocation=common-py-inserting-data", "error-valuenotallnum":"?redirectsource=savechanges&changessaved=error-valuenotallnum"}
        for key in results.keys():
            if result == key:
                return web.HTTPFound('http://' + currentdomain + '/other-projects/maximilian/' + path + results[result])
        return web.HTTPFound('http://' + currentdomain + '/other-projects/maximilian/' + path + "?redirectsource=savechanges&changessaved=error-other&error="+ result +"&errorlocation=common-py-inserting-data")
    except Exception as e:
        print("Error: " + str(e) + ".")
        return web.HTTPFound('http://' + currentdomain + '/other-projects/maximilian/' + path + '?redirectsource=savechanges&changesaved=error-other&error=\''+str(e)+'\'&errorlocation=savechanges-api')


app = web.Application()
app.add_routes(routes)
web.run_app(app, port=5000)
