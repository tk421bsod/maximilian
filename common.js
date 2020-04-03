 //common.js contains some common functions used throughout the web interface

function save(path){
    let querystring = []
    var firstparturl="http://animationdoctorstudio.net:5000/other-projects/maximilian/api/" + path + "?"
    //when button is clicked, check if fields are empty, from the top down
    var inputs, index;
    inputs = document.getElementsByTagName('input');
    for (index = 0; index < inputs.length; ++index) {
        console.log(inputs[index].name)
        var idvalue=inputs[index]
        if (idvalue.value=="") {
            //if field is empty, say that it's empty
            document.getElementById("error").innerHTML="The " + inputs[index].name + " field is empty, and there may be other fields that are empty. Make sure to fill every field out before clicking 'Save Changes'. ";
            return;
        }
        querystring.push(inputs[index].name + "=" + inputs[index].value + "&" );
    }
    for (const element of querystring) {
        var url=firstparturl+element
        var firstparturl=url
    }

    //if no fields are empty, don't display error message
    document.getElementById("error").innerHTML = ""
    //show that response is being saved
    document.getElementById("saving").innerHTML="Saving...";
    //redirect to that url
    window.location.href = url;
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