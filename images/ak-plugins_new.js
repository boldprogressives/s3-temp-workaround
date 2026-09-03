// Place any jQuery/helper plugins in here.
/* Lightbox Functions */
/* Serialize object into AJAX friendly array */
$.fn.serializeObject = function() {
	var o = {};
	var a = this.serializeArray();
	$.each(a, function() {
		if (o[this.name]) {
			if (!o[this.name].push) {
				o[this.name] = [o[this.name]];
			}
			o[this.name].push(this.value || '');
		} else {
			o[this.name] = this.value || '';
		}
	});
	return o;
};
/* Handle the form submission.
 Use ajax submission with data to AK from form.
 Submit to page value (hidden form input) */
function submitLightbox(form) {
	var the_form = $("#" + form);
	var form_data = the_form.serializeObject();
	var page = the_form.find('.page').val();
	if (!validate(the_form)) {
		$("#lightbox_error").fadeIn();
		return false;
	}
	$("#lightbox_error").fadeOut();
	$.post(page, form_data).success(function(result, data) {
		console.log(data);
		if (data == "success") {
			handleActionkitSuccess();
		} else {
			handleActionkitError(data.errors, the_form);
		}
	});
	console.log("submitLightbox");
	console.log(the_form);
	console.log(form_data);
	console.log(page);
}

function validate(form) {
	if ($("#lightbox_error").length === 0) {
		form.prepend("<div id=\"lightbox_error\" style=\"display:none\"></div>");
	} else {
		$("#lightbox_error").html("");
	}
	var valid = true;
	var val_email = form.find("input[name=email]").val();
	if (!val_email || !validators.email(val)) {
		form.find("input[name=email]").css("background-color", "pink");
		$("#lightbox_error").append("<p>Please type a valid email address.</p>");
		valid = false;
	} else {
		form.find("input[name=email]").css("background-color", "white");
	}
	var val_zip = form.find("input[name=zip]").val();
	if (!val_zip || !validators.zip(val)) {
		form.find("input[name=zip]").css("background-color", "pink");
		$("#lightbox_error").append("<p>Please type a valid zipcode.</p>");
		valid = false;
	} else {
		form.find("input[name=zip]").css("background-color", "white");
	}
	return valid;
}
validators = {};
validators.email = function(value) {
	if (!/^\s*\S+@\S+\.\S+\s*$/.test(value)) return false;
	return true;
};
validators.zip = function(value) {
	if (!/\d{5}/.test(value)) return false;
	return true;
};
/* Handle and track errors for validation.
  Add error class to invalid inputs */
function handleActionkitError(errors, form) {
	if ($("#lightbox_error").length === 0) {
		form.prepend("<div id=\"lightbox_error\" style=\"display:none\"></div>");
	} else {
		$("#lightbox_error").html("");
	}
	$('.error').removeClass('error');
	$.each(errors, function(i, n) {
		form.find("#" + i).addClass("error");
		$("#lightbox_error").append("<p>Error on " + i + ": " + n + ".</p>");
	});
	$("#lightbox_error").fadeIn();
}
/* Handle Action Kit submission success
 Form fades out to reveal a thanks message.
 Easy to escape from here with esc key or
 Clicking X or out of lightbox
*/
function handleActionkitSuccess() {
	$(".lightbox").fadeOut(function() {
		$("#lightbox_error").fadeOut();
		$("#thanks").fadeIn(function() {
			$(document).keyup(function(e) {
				if (e.keyCode == 27) { // esc keycode
					$('#thanks').fadeOut();
					$('#overlay').fadeOut();
				}
			});
		});
		$("#overlay").click(function() {
			$("#thanks").fadeOut();
			$(this).fadeOut();
		});
	});
}
// functions to deal with splash page cookie
/*
   name - name of the cookie
   value - value of the cookie
   [expires] - expiration date of the cookie
     (defaults to end of current session)
   [path] - path for which the cookie is valid
     (defaults to path of calling document)
   [domain] - domain for which the cookie is valid
     (defaults to domain of calling document)
   [secure] - Boolean value indicating if the cookie transmission requires
     a secure transmission
   * an argument defaults when it is assigned null as a placeholder
   * a null placeholder is not required for trailing omitted arguments
*/
function setCookie(name, value, expires, path, domain, secure) {
	var curCookie = name + "=" + escape(value) + ((expires) ? "; expires=" + expires.toGMTString() : "") + ((path) ? "; path=" + path : "") + ((domain) ? "; domain=" + domain : "") + ((secure) ? "; secure" : "");
	document.cookie = curCookie;
}
/*
  name - name of the desired cookie
  return string containing value of specified cookie or null
  if cookie does not exist
*/
function getCookie(name) {
	var dc = document.cookie;
	var prefix = name + "=";
	var begin = dc.indexOf("; " + prefix);
	if (begin == -1) {
		begin = dc.indexOf(prefix);
		if (begin !== 0) return null;
	} else begin += 2;
	var end = document.cookie.indexOf(";", begin);
	if (end == -1) end = dc.length;
	return unescape(dc.substring(begin + prefix.length, end));
}
/*
   name - name of the cookie
   [path] - path of the cookie (must be same as path used to create cookie)
   [domain] - domain of the cookie (must be same as domain used to
     create cookie)
   path and domain default if assigned null or omitted if no explicit
     argument proceeds
*/
function deleteCookie(name, path, domain) {
	if (getCookie(name)) {
		document.cookie = name + "=" + ((path) ? "; path=" + path : "") + ((domain) ? "; domain=" + domain : "") + "; expires=Thu, 01-Jan-70 00:00:01 GMT";
	}
}
// date - any instance of the Date object
// * hand all instances of the Date object to this function for "repairs"

function fixDate(date) {
	var base = new Date(0);
	var skew = base.getTime();
	if (skew > 0) date.setTime(date.getTime() - skew);
}

function lightboxLogic() {
	console.log('lightbox stuff');
	//Check page type first
	if ($('body').hasClass('petition-page') || $('body').hasClass('survey-page') || $('body').hasClass('signup-page')) {
		//Check actionkit args to see if user is recognized
		if (actionkit.context && actionkit.context.recognizeduser) {
			//Set cookie if user is recognized
			setRecognizedCookie();
		}
		// only display lightbox if visitors aren't coming from email, but cookie them anyway
		if (!getCookie("recognizedUser")) {
			runLightbox();
		}
	}
}

function setRecognizedCookie() {
	var now = new Date();
	fixDate(now);
	now.setTime(now.getTime() + 365 * 24 * 60 * 60 * 1000);
	setCookie("recognizedUser", "recognized", now);
}

function runLightbox() {
	//displayLightbox('#splash-lightbox');
	/* Auto display signup form after 3 seconds */
	setTimeout(function() {
		$("#signup_form").fadeIn(function() {
			$(document).keyup(function(e) {
				if (e.keyCode == 27) { // esc keycode
					$('#signup_form').fadeOut();
					$('#overlay').fadeOut();
				}
			});
		});
		$("#overlay").fadeIn();
	}, 3000);
	//Set cookie so user won't see it next time
	setRecognizedCookie();
}
var baseOnContextLoaded = actionkit.forms.onContextLoaded;
actionkit.forms.onContextLoaded = function(context) {
	baseOnContextLoaded(context);
	lightboxLogic();
};
$(document).ready(function() { /* Close any lightbox by clicking X */
	$(document).on('click', '.close_box', function() {
		$(this).parent('.lightbox').fadeOut();
		$('#overlay').fadeOut();
	});
});
/* Handle Yes/No survey question.
/* Return with sign up form on Yes.
/* Close lightbox and overlay on No. */
/* function handleQuestion(answer) {
  $("#question").fadeOut();
    
    if(answer == 'yes') {
    $("#form").fadeIn();
      } else {
        $("#overlay").fadeOut();
      }
} */
/* Event listener for question buttons */
/* $('#question button').click(function() {
      handleQuestion($(this).val());
    }); */
/* old code,delete if QA goes well
 * show lightbox for folks who aren't cookied
 */
// create an instance of the Date object
/*	var now = new Date();
		// fix the bug in Navigator 2.0, Macintosh
		fixDate(now);
/*
      cookie expires in one year (actually, 365 days)
      365 days in a year
      24 hours in a day
      60 minutes in an hour
      60 seconds in a minute
      1000 milliseconds in a second
      */
/*	now.setTime(now.getTime() + 365 * 24 * 60 * 60 * 1000);
/*		testValue = Math.floor(10 * Math.random());
		setCookie("AreCookiesEnabled", testValue);
		if (testValue == getCookie("AreCookiesEnabled")) {
			// EDIT SPLASH PAGE COOKIE HERE!! ************************************************/
/*var splash_cookie = "counter20";
      
      var visits = getCookie(splash_cookie);
      // if the cookie wasn't found, this is your first visit
      if (!visits || visits <= 0) {
        
        visits = 1; // the value for the new cookie
        console.log("visits"+visits);
        */
/*      } else {
      
        if(visits >= 20) {
          visits = 0;
             document.cookie = splash_cookie + '=; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
        } else{
      
        // increment the counter
        visits = parseInt(visits) + 1;
      
      }
      }
      // set the new cookie
      setCookie(splash_cookie, visits, now);
          } // end cookie block
      
  }*/