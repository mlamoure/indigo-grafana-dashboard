(window.webpackJsonp=window.webpackJsonp||[]).push([[24],{"4kIt":function(n,e,t){"use strict";var r=t("q1tI"),o=t.n(r),a=t("kDLi").LegacyForms.Input;e.a=function(n){var e=n.onSubmit,t=n.onOrgNameChange,r=n.orgName;return o.a.createElement("div",null,o.a.createElement("h3",{className:"page-sub-heading"},"Organization profile"),o.a.createElement("form",{name:"orgForm",className:"gf-form-group",onSubmit:function(n){n.preventDefault(),e()}},o.a.createElement("div",{className:"gf-form-inline"},o.a.createElement("div",{className:"gf-form max-width-28"},o.a.createElement("span",{className:"gf-form-label"},"Organization name"),o.a.createElement(a,{className:"gf-form-input",type:"text",onChange:function(n){return t(n.target.value)},value:r}))),o.a.createElement("div",{className:"gf-form-button-row"},o.a.createElement("button",{type:"submit",className:"btn btn-primary"},"Save"))))}},e5mm:function(n,e,t){"use strict";t.r(e),function(n){t.d(e,"OrgDetailsPage",(function(){return O}));var r=t("q1tI"),o=t.n(r),a=t("0cfB"),i=t("/MKj"),u=t("ZGyg"),c=t("4kIt"),f=t("mHLn"),s=t("vl1P"),l=t("lzJ5"),p=t("fZn8");function m(n){return(m="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(n){return typeof n}:function(n){return n&&"function"==typeof Symbol&&n.constructor===Symbol&&n!==Symbol.prototype?"symbol":typeof n})(n)}function g(n,e,t,r,o,a,i){try{var u=n[a](i),c=u.value}catch(n){return void t(n)}u.done?e(c):Promise.resolve(c).then(r,o)}function v(n,e){if(!(n instanceof e))throw new TypeError("Cannot call a class as a function")}function b(n,e){for(var t=0;t<e.length;t++){var r=e[t];r.enumerable=r.enumerable||!1,r.configurable=!0,"value"in r&&(r.writable=!0),Object.defineProperty(n,r.key,r)}}function h(n,e){return!e||"object"!==m(e)&&"function"!=typeof e?function(n){if(void 0===n)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return n}(n):e}function y(n){return(y=Object.setPrototypeOf?Object.getPrototypeOf:function(n){return n.__proto__||Object.getPrototypeOf(n)})(n)}function d(n,e){return(d=Object.setPrototypeOf||function(n,e){return n.__proto__=e,n})(n,e)}var O=function(n){function e(){var n,t;v(this,e);for(var r=arguments.length,o=new Array(r),a=0;a<r;a++)o[a]=arguments[a];return(t=h(this,(n=y(e)).call.apply(n,[this].concat(o)))).onOrgNameChange=function(n){t.props.setOrganizationName(n)},t.onUpdateOrganization=function(){t.props.updateOrganization()},t}var t,r,a,i,s;return function(n,e){if("function"!=typeof e&&null!==e)throw new TypeError("Super expression must either be null or a function");n.prototype=Object.create(e&&e.prototype,{constructor:{value:n,writable:!0,configurable:!0}}),e&&d(n,e)}(e,n),t=e,(r=[{key:"componentDidMount",value:(i=regeneratorRuntime.mark((function n(){return regeneratorRuntime.wrap((function(n){for(;;)switch(n.prev=n.next){case 0:return n.next=2,this.props.loadOrganization();case 2:case"end":return n.stop()}}),n,this)})),s=function(){var n=this,e=arguments;return new Promise((function(t,r){var o=i.apply(n,e);function a(n){g(o,t,r,a,u,"next",n)}function u(n){g(o,t,r,a,u,"throw",n)}a(void 0)}))},function(){return s.apply(this,arguments)})},{key:"render",value:function(){var n=this,e=this.props,t=e.navModel,r=e.organization,a=0===Object.keys(r).length;return o.a.createElement(u.a,{navModel:t},o.a.createElement(u.a.Contents,{isLoading:a},!a&&o.a.createElement("div",null,o.a.createElement(c.a,{onOrgNameChange:function(e){return n.onOrgNameChange(e)},onSubmit:this.onUpdateOrganization,orgName:r.name}),o.a.createElement(f.b,{resourceUri:"org"}))))}}])&&b(t.prototype,r),a&&b(t,a),e}(r.PureComponent);var w={loadOrganization:s.a,setOrganizationName:p.c,updateOrganization:s.b};e.default=Object(a.hot)(n)(Object(i.connect)((function(n){return{navModel:Object(l.a)(n.navIndex,"org-settings"),organization:n.organization.organization}}),w)(O))}.call(this,t("3UD+")(n))},vl1P:function(n,e,t){"use strict";t.d(e,"a",(function(){return u})),t.d(e,"b",(function(){return c}));var r=t("t8hP"),o=t("fZn8");function a(n,e,t,r,o,a,i){try{var u=n[a](i),c=u.value}catch(n){return void t(n)}u.done?e(c):Promise.resolve(c).then(r,o)}function i(n){return function(){var e=this,t=arguments;return new Promise((function(r,o){var i=n.apply(e,t);function u(n){a(i,r,o,u,c,"next",n)}function c(n){a(i,r,o,u,c,"throw",n)}u(void 0)}))}}function u(){return function(){var n=i(regeneratorRuntime.mark((function n(e){var t;return regeneratorRuntime.wrap((function(n){for(;;)switch(n.prev=n.next){case 0:return n.next=2,Object(r.getBackendSrv)().get("/api/org");case 2:return t=n.sent,e(Object(o.b)(t)),n.abrupt("return",t);case 5:case"end":return n.stop()}}),n)})));return function(e){return n.apply(this,arguments)}}()}function c(){return function(){var n=i(regeneratorRuntime.mark((function n(e,t){var o;return regeneratorRuntime.wrap((function(n){for(;;)switch(n.prev=n.next){case 0:return o=t().organization.organization,n.next=3,Object(r.getBackendSrv)().put("/api/org",{name:o.name});case 3:e(u());case 4:case"end":return n.stop()}}),n)})));return function(e,t){return n.apply(this,arguments)}}()}}}]);
//# sourceMappingURL=OrgDetailsPage.017a0d1a58b1119d038d.js.map