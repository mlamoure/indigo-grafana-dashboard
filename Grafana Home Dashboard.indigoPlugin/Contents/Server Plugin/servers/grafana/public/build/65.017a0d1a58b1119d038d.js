(window.webpackJsonp=window.webpackJsonp||[]).push([[65],{EZhu:function(e,n,r){"use strict";r.d(n,"a",(function(){return l}));var t=r("q1tI"),a=r.n(t),o=r("ZFWI"),i=r("kDLi"),s=r("kDDq");function u(){var e=function(e,n){n||(n=e.slice(0));return Object.freeze(Object.defineProperties(e,{raw:{value:Object.freeze(n)}}))}(["\n        max-width: 400px;\n      "]);return u=function(){return e},e}var l=function(e){var n=e.onChangePassword,r=e.isSaving,t=o.b.ldapEnabled,l=o.b.authProxyEnabled;return t||l?a.a.createElement("p",null,"You cannot change password when ldap or auth proxy authentication is enabled."):a.a.createElement("div",{className:Object(s.css)(u())},a.a.createElement(i.Form,{onSubmit:n},(function(e){var n,t,s,u=e.register,l=e.errors,c=e.getValues;return a.a.createElement(a.a.Fragment,null,a.a.createElement(i.Field,{label:"Old password",invalid:!!l.oldPassword,error:null==l?void 0:null===(n=l.oldPassword)||void 0===n?void 0:n.message},a.a.createElement(i.Input,{type:"password",name:"oldPassword",ref:u({required:"Old password is required"})})),a.a.createElement(i.Field,{label:"New password",invalid:!!l.newPassword,error:null==l?void 0:null===(t=l.newPassword)||void 0===t?void 0:t.message},a.a.createElement(i.Input,{type:"password",name:"newPassword",ref:u({required:"New password is required",validate:{confirm:function(e){return e===c().confirmNew||"Passwords must match"},old:function(e){return e!==c().oldPassword||"New password can't be the same as the old one."}}})})),a.a.createElement(i.Field,{label:"Confirm password",invalid:!!l.confirmNew,error:null==l?void 0:null===(s=l.confirmNew)||void 0===s?void 0:s.message},a.a.createElement(i.Input,{type:"password",name:"confirmNew",ref:u({required:"New password confirmation is required",validate:function(e){return e===c().newPassword||"Passwords must match"}})})),a.a.createElement(i.HorizontalGroup,null,a.a.createElement(i.Button,{variant:"primary",disabled:r},"Change Password"),a.a.createElement(i.LinkButton,{variant:"secondary",href:"".concat(o.b.appSubUrl,"/profile")},"Cancel")))})))}},PEdC:function(e,n,r){"use strict";r.r(n),function(e){r.d(n,"ChangePasswordPage",(function(){return v}));var t=r("q1tI"),a=r.n(t),o=r("0cfB"),i=r("/MKj"),s=r("lzJ5"),u=r("V9sw"),l=r("ZGyg"),c=r("EZhu");function d(e){return(d="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(e){return typeof e}:function(e){return e&&"function"==typeof Symbol&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e})(e)}function f(e,n){if(!(e instanceof n))throw new TypeError("Cannot call a class as a function")}function p(e,n){for(var r=0;r<n.length;r++){var t=n[r];t.enumerable=t.enumerable||!1,t.configurable=!0,"value"in t&&(t.writable=!0),Object.defineProperty(e,t.key,t)}}function w(e,n){return!n||"object"!==d(n)&&"function"!=typeof n?function(e){if(void 0===e)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return e}(e):n}function m(e){return(m=Object.setPrototypeOf?Object.getPrototypeOf:function(e){return e.__proto__||Object.getPrototypeOf(e)})(e)}function b(e,n){return(b=Object.setPrototypeOf||function(e,n){return e.__proto__=n,e})(e,n)}var v=function(e){function n(){return f(this,n),w(this,m(n).apply(this,arguments))}var r,t,o;return function(e,n){if("function"!=typeof n&&null!==n)throw new TypeError("Super expression must either be null or a function");e.prototype=Object.create(n&&n.prototype,{constructor:{value:e,writable:!0,configurable:!0}}),n&&b(e,n)}(n,e),r=n,(t=[{key:"render",value:function(){var e=this.props.navModel;return a.a.createElement(l.a,{navModel:e},a.a.createElement(u.a,null,(function(e,n){var r=e.changePassword;return a.a.createElement(l.a.Contents,null,a.a.createElement("h3",{className:"page-sub-heading"},"Change Your Password"),a.a.createElement(c.a,{onChangePassword:r,isSaving:n.changePassword}))})))}}])&&p(r.prototype,t),o&&p(r,o),n}(t.PureComponent);n.default=Object(o.hot)(e)(Object(i.connect)((function(e){return{navModel:Object(s.a)(e.navIndex,"change-password")}}),{})(v))}.call(this,r("3UD+")(e))}}]);
//# sourceMappingURL=65.017a0d1a58b1119d038d.js.map