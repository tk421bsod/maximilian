 //common.js: common functions used throughout the web interface put together in one file
function save(path, database, table, valuenodupe, valueallnum, debug){
    //this function is ran client-side, and data gets passed to it through parameters
    //basically this takes data, does some checks to validate it, displays an error message if it's not valid, then passes the data to maximilian-api-savechanges.py through a query string
    try {
    let querystring = []
    var firstparturl="http://animationdoctorstudio.net:5000/other-projects/maximilian/api?"
    var inputs, index;
    //gets list of input elements
    inputs = document.getElementsByTagName('input');
    //for each input element
    for (index = 0; index < inputs.length; ++index) {
        var idvalue=inputs[index]
        //check if that input field is empty
        if (idvalue.value=="") {
            //if field is empty, display error message
            document.getElementById("error").innerHTML="The " + inputs[index].name + " field is empty, and there may be other fields that are empty. Make sure to fill every field out before clicking 'Save Changes'. ";
            return;
        }
        //if that field isn't empty, concatenate a part of the query string
        querystring.push(inputs[index].name + "=" + inputs[index].value + "&" );
    }
    //after that finishes, for each element in querystring
    for (const element of querystring) {
        //add that element to firstparturl
        var url=firstparturl+element
        //and set firstparturl to url, adding on to url with a new parameter for each input element
        var firstparturl=url
    }
    //then add other parameters to the url, specified in arguments
    var otherparams = "path=" + path + "&database=" + database + "&table=" + table + "&valuenodupe=" + valuenodupe + "&debug=" + debug + "&valueallnum=" + valueallnum
    var url = url + otherparams
    //if no fields are empty, don't display error message
    document.getElementById("error").innerHTML = "";
    //show that changes are being saved
    document.getElementById("saving").innerHTML="Saving...";
    //redirect to that url
    window.location.href = url;
    } catch (error) {
        document.getElementById("error").innerHTML = "There was an error while saving changes. Please try again later.";
        document.getElementById("saving").innerHTML="";
        console.error(error)
        var technicalinfo = "Error: " + error.message + ". This error was client-side, and it occured in common.js.";
        buttonclicked = 0;
        document.getElementById("technicalinfobutton").innerHTML = "Click to show technical info";
        document.getElementById("technicalinfobutton").style.opacity = "1";
        document.getElementById("technicalinfo").innerHTML = technicalinfo;
        throw error
        
        return;
    }
}
    function getUrlVars() {
        var vars = {};
        var parts = window.location.href.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(m,key,value) {
            vars[key] = value;
        });
        return vars;
    }
function getUrlParam(parameter, defaultvalue){
    var urlparameter = defaultvalue;
    if(window.location.href.indexOf(parameter) > -1){
        urlparameter = getUrlVars()[parameter];
        }
        return urlparameter;
    }
function showtechnicalinfo(){
    buttonclicked=buttonclicked+1;
    if (Math.abs(buttonclicked % 2) == 1){
        document.getElementById("technicalinfobutton").innerHTML="Click to hide technical info"
        document.getElementById("technicalinfo").style.height="auto"
        document.getElementById("technicalinfo").style.opacity="1"
    }
    else{
        document.getElementById("technicalinfobutton").innerHTML="Click to show technical info"
        document.getElementById("technicalinfo").style.height="0"
        document.getElementById("technicalinfo").style.opacity="0"
    }
}