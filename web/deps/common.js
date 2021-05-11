//some stuff that's used pretty much everywhere

function save(path, database, table, valuenodupe, valueallnum, valueallnumenabled, debug){
    try {
    let querystring = []
    var currenturl=window.location.hostname;
    console.log(currenturl);
    var firstparturl=currenturl+":5000/other-projects/maximilian/api?";
    var inputs, index;
    inputs = document.getElementsByTagName('input');
    for (index = 0; index < inputs.length; ++index) {
        var idvalue=inputs[index]
        if (idvalue.value=="") {
            document.getElementById("error").innerHTML="The " + inputs[index].name + " field is empty, and there may be other fields that are empty. Make sure to fill every field out. ";
            return;
        }
        querystring.push(inputs[index].name + "=" + inputs[index].value + "&" );
    }
    for (const element of querystring) {
        var url=firstparturl+element
        var firstparturl=url
    }
    var otherparams = "path=" + path + "&database=" + database + "&table=" + table + "&valuenodupe=" + valuenodupe + "&valueallnum=" + valueallnum + "&valueallnumenabled=" + valueallnumenabled + "&currentdomain=" + window.location.hostname + ":" + window.location.port;
    if(debug!=""){
        var otherparams=otherparams+"&debug="+debug;
    }
    var url = 'http://' + url + otherparams;
    document.getElementById("error").innerHTML = "";
    document.getElementById("saving").innerHTML="Saving...";
    window.location.href = url;
    } catch (error) {
        console.error(error)
        var message = "Error: " + error.message + ". This error was client-side, and it occured in common.js.";
        displayError("save", message)
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

function displayError(origin, message){
    const origins = {"saveresponse":"saving a command", "saveroles":"saving reaction roles", "postrequest":"accessing data", "save":"saving data"};
    //maybe we should show a toast notification if there's an error
    //display error message
    document.getElementById("error").innerHTML = "There was an error while " + origins[origin] + ". Please try again later.";
    if (origin == "savechanges" || origin == "saveroles" || origin == "save"){
        document.getElementById("saving").innerHTML="";
    }
    //then show button that toggles more detailed info
    document.getElementById("technicalinfobutton").innerHTML = "Click to show technical info";
    document.getElementById("technicalinfobutton").style.opacity = "1";
    document.getElementById("technicalinfo").innerHTML = message;
}

function showTechnicalInfo(){
    try{
    buttonclicked=buttonclicked+1;
    } catch (ReferenceError){
    var buttonclicked = 0;
    }
    if (Math.abs(buttonclicked % 2) == 1){
        document.getElementById("technicalinfobutton").innerHTML="Click to hide technical info";
        document.getElementById("technicalinfo").style.height="auto";
        document.getElementById("technicalinfo").style.opacity="1";
    }
    else{
        document.getElementById("technicalinfobutton").innerHTML="Click to show technical info";
        document.getElementById("technicalinfo").style.height="0";
        document.getElementById("technicalinfo").style.opacity="0";
    }
}

function isKeyInObject(object, value){
    for (k in object) {
        if (k == value) {
            return true;
        }
    }
    return false;
}
    
function isValueInObject(object, value){
    for (k in object) {
        if (object[k] == value) {
            return true;
        }
    }
    return false;
}

function handlePossibleErrors(origin){
    var sourceOfRedirect = getUrlParam('redirectsource','noredirect');
    var saveState = getUrlParam('changessaved', '');
    var errorMessage = getUrlParam('error', '');
    const saveResponseErrors = {"success":"Your custom command was saved successfully. Try testing it!", "error-duplicate":"Your custom command already exists. Try making a new one!", "error-valuenotallnum":"It looks like the server ID isn't valid. Make sure that you entered everything in the correct fields. Remember, the server ID is not the server's name."};
    if (sourceOfRedirect == "savechanges" && origin == "responses" && isKeyInObject(saveResponseErrors, saveState)){
        if (saveState.includes("error")){
            document.getElementById("error").innerHTML = saveResponseErrors[saveState];
        }
        else {
            document.getElementById("saving").innerHTML = saveResponseErrors[saveState]; 
        }
    } else {
        if(errorMessage != ""){
            console.error(errorMessage);
            message = errorMessage + ". This error was server-side, and it occurred in " + getUrlParam('errorlocation', '') + '.';
            displayError("saveresponse", message);
        }
   } 
}