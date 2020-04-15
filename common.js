 //common.js: common functions used throughout the web interface put together in one file

function save(path, database, table, valuenodupe, debug){
    try {
    let querystring = []
    var firstparturl="http://animationdoctorstudio.net:5000/other-projects/maximilian/api?"
    var inputs, index;
    //gets list of input elements
    inputs = document.getElementsByTagName('input');
    //for each input element
    for (index = 0; index < inputs.length; ++index) {
        //log the name of the element
        var idvalue=inputs[index]
        //and check if that input field is empty
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
    var otherparams = "path=" + path + "&database=" + database + "&table=" + table + "&valuenodupe=" + valuenodupe + "&debug=" + debug
    var url = url + otherparams
    //if no fields are empty, don't display error message
    document.getElementById("error").innerHTML = "";
    //show that response is being saved
    document.getElementById("saving").innerHTML="Saving...";
    //redirect to that url
    window.location.href = url;
    }
    catch (error) {
        console.log(error);
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