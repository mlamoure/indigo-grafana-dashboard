(window.webpackJsonp=window.webpackJsonp||[]).push([[31],{"8uRs":function(e,t,n){"use strict";n.d(t,"b",(function(){return a})),n.d(t,"a",(function(){return o})),n.d(t,"d",(function(){return i})),n.d(t,"g",(function(){return c})),n.d(t,"c",(function(){return u})),n.d(t,"f",(function(){return s})),n.d(t,"e",(function(){return l})),n.d(t,"i",(function(){return m})),n.d(t,"h",(function(){return f}));var r=n("GQ3c"),a=function(e){return e.searchQuery},o=function(e){return e.searchMemberQuery},i=function(e){return e.groups},c=function(e){return e.teams.length},u=function(e,t){return e.team.id===parseInt(t,10)?e.team:null},s=function(e){var t=RegExp(e.searchQuery,"i");return e.teams.filter((function(e){return t.test(e.name)}))},l=function(e){var t=RegExp(e.searchMemberQuery,"i");return e.members.filter((function(e){return t.test(e.login)||t.test(e.email)||t.test(e.name)}))},m=function(e){var t=e.members,n=e.signedInUser,a=e.editorsCanAdmin,o=t.find((function(e){return e.userId===n.id})),i=o?o.permission:r.TeamPermissionLevel.Member;return f({permission:i,signedInUser:n,editorsCanAdmin:a})},f=function(e){var t=e.permission,n=e.signedInUser,a=e.editorsCanAdmin,o=n.isGrafanaAdmin||n.orgRole===r.OrgRole.Admin,i=t===r.TeamPermissionLevel.Admin;return o||i||!a}},Rczg:function(e,t,n){"use strict";var r=n("q1tI"),a=n.n(r),o=n("/MKj"),i=n("kDLi"),c=n("mHLn"),u=n("gxTa"),s=n("X+V3"),l=n("8uRs");function m(e){return(m="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(e){return typeof e}:function(e){return e&&"function"==typeof Symbol&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e})(e)}function f(e,t){for(var n=0;n<t.length;n++){var r=t[n];r.enumerable=r.enumerable||!1,r.configurable=!0,"value"in r&&(r.writable=!0),Object.defineProperty(e,r.key,r)}}function p(e,t){return!t||"object"!==m(t)&&"function"!=typeof t?function(e){if(void 0===e)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return e}(e):t}function d(e){return(d=Object.setPrototypeOf?Object.getPrototypeOf:function(e){return e.__proto__||Object.getPrototypeOf(e)})(e)}function b(e,t){return(b=Object.setPrototypeOf||function(e,t){return e.__proto__=t,e})(e,t)}var g=i.LegacyForms.Input,h=function(e){function t(e){var n;return function(e,t){if(!(e instanceof t))throw new TypeError("Cannot call a class as a function")}(this,t),(n=p(this,d(t).call(this,e))).onChangeName=function(e){n.setState({name:e.target.value})},n.onChangeEmail=function(e){n.setState({email:e.target.value})},n.onUpdate=function(e){var t=n.state,r=t.name,a=t.email;e.preventDefault(),n.props.updateTeam(r,a)},n.state={name:e.team.name,email:e.team.email},n}var n,r,o;return function(e,t){if("function"!=typeof t&&null!==t)throw new TypeError("Super expression must either be null or a function");e.prototype=Object.create(t&&t.prototype,{constructor:{value:e,writable:!0,configurable:!0}}),t&&b(e,t)}(t,e),n=t,(r=[{key:"render",value:function(){var e=this.props.team,t=this.state,n=t.name,r=t.email;return a.a.createElement("div",null,a.a.createElement("h3",{className:"page-sub-heading"},"Team Settings"),a.a.createElement("form",{name:"teamDetailsForm",className:"gf-form-group",onSubmit:this.onUpdate},a.a.createElement("div",{className:"gf-form max-width-30"},a.a.createElement(i.InlineFormLabel,null,"Name"),a.a.createElement(g,{type:"text",required:!0,value:n,className:"gf-form-input max-width-22",onChange:this.onChangeName})),a.a.createElement("div",{className:"gf-form max-width-30"},a.a.createElement(i.InlineFormLabel,{tooltip:"This is optional and is primarily used to set the team profile avatar (via gravatar service)"},"Email"),a.a.createElement(g,{type:"email",className:"gf-form-input max-width-22",value:r,placeholder:"team@email.com",onChange:this.onChangeEmail})),a.a.createElement("div",{className:"gf-form-button-row"},a.a.createElement("button",{type:"submit",className:"btn btn-primary"},"Update"))),a.a.createElement(c.a,{resourceUri:"teams/".concat(e.id)}))}}])&&f(n.prototype,r),o&&f(n,o),t}(a.a.Component);var y={updateTeam:u.j};t.a=Object(o.connect)((function(e){var t=Object(s.c)(e.location);return{team:Object(l.c)(e.team,t)}}),y)(h)},WB4m:function(e,t,n){"use strict";var r=n("q1tI"),a=n.n(r),o=n("/MKj"),i=n("BVom"),c=n("kDLi"),u=n("gxTa"),s=n("8uRs"),l=n("QQVG");function m(e){return(m="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(e){return typeof e}:function(e){return e&&"function"==typeof Symbol&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e})(e)}function f(e,t,n,r,a,o,i){try{var c=e[o](i),u=c.value}catch(e){return void n(e)}c.done?t(u):Promise.resolve(u).then(r,a)}function p(e,t){for(var n=0;n<t.length;n++){var r=t[n];r.enumerable=r.enumerable||!1,r.configurable=!0,"value"in r&&(r.writable=!0),Object.defineProperty(e,r.key,r)}}function d(e,t){return!t||"object"!==m(t)&&"function"!=typeof t?function(e){if(void 0===e)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return e}(e):t}function b(e){return(b=Object.setPrototypeOf?Object.getPrototypeOf:function(e){return e.__proto__||Object.getPrototypeOf(e)})(e)}function g(e,t){return(g=Object.setPrototypeOf||function(e,t){return e.__proto__=t,e})(e,t)}var h=c.LegacyForms.Input,y="Sync LDAP or OAuth groups with your Grafana teams.",v=function(e){function t(e){var n;return function(e,t){if(!(e instanceof t))throw new TypeError("Cannot call a class as a function")}(this,t),(n=d(this,b(t).call(this,e))).onToggleAdding=function(){n.setState({isAdding:!n.state.isAdding})},n.onNewGroupIdChanged=function(e){n.setState({newGroupId:e.target.value})},n.onAddGroup=function(e){e.preventDefault(),n.props.addTeamGroup(n.state.newGroupId),n.setState({isAdding:!1,newGroupId:""})},n.onRemoveGroup=function(e){n.props.removeTeamGroup(e.groupId)},n.state={isAdding:!1,newGroupId:""},n}var n,r,o,u,s;return function(e,t){if("function"!=typeof t&&null!==t)throw new TypeError("Super expression must either be null or a function");e.prototype=Object.create(t&&t.prototype,{constructor:{value:e,writable:!0,configurable:!0}}),t&&g(e,t)}(t,e),n=t,(r=[{key:"componentDidMount",value:function(){this.fetchTeamGroups()}},{key:"fetchTeamGroups",value:(u=regeneratorRuntime.mark((function e(){return regeneratorRuntime.wrap((function(e){for(;;)switch(e.prev=e.next){case 0:return e.next=2,this.props.loadTeamGroups();case 2:case"end":return e.stop()}}),e,this)})),s=function(){var e=this,t=arguments;return new Promise((function(n,r){var a=u.apply(e,t);function o(e){f(a,n,r,o,i,"next",e)}function i(e){f(a,n,r,o,i,"throw",e)}o(void 0)}))},function(){return s.apply(this,arguments)})},{key:"isNewGroupValid",value:function(){return this.state.newGroupId.length>1}},{key:"renderGroup",value:function(e){var t=this;return a.a.createElement("tr",{key:e.groupId},a.a.createElement("td",null,e.groupId),a.a.createElement("td",{style:{width:"1%"}},a.a.createElement("a",{className:"btn btn-danger btn-small",onClick:function(){return t.onRemoveGroup(e)}},a.a.createElement(c.Icon,{name:"times",style:{marginBottom:0}}))))}},{key:"render",value:function(){var e=this,t=this.state,n=t.isAdding,r=t.newGroupId,o=this.props.groups;return a.a.createElement("div",null,a.a.createElement("div",{className:"page-action-bar"},a.a.createElement("h3",{className:"page-sub-heading"},"External group sync"),a.a.createElement(c.Tooltip,{placement:"auto",content:y},a.a.createElement(c.Icon,{className:"icon--has-hover page-sub-heading-icon",name:"question-circle"})),a.a.createElement("div",{className:"page-action-bar__spacer"}),o.length>0&&a.a.createElement("button",{className:"btn btn-primary pull-right",onClick:this.onToggleAdding},a.a.createElement(c.Icon,{name:"plus"})," Add group")),a.a.createElement(i.a,{in:n},a.a.createElement("div",{className:"cta-form"},a.a.createElement("button",{className:"cta-form__close btn btn-transparent",onClick:this.onToggleAdding},a.a.createElement(c.Icon,{name:"times"})),a.a.createElement("h5",null,"Add External Group"),a.a.createElement("form",{className:"gf-form-inline",onSubmit:this.onAddGroup},a.a.createElement("div",{className:"gf-form"},a.a.createElement(h,{type:"text",className:"gf-form-input width-30",value:r,onChange:this.onNewGroupIdChanged,placeholder:"cn=ops,ou=groups,dc=grafana,dc=org"})),a.a.createElement("div",{className:"gf-form"},a.a.createElement("button",{className:"btn btn-primary gf-form-btn",type:"submit",disabled:!this.isNewGroupValid()},"Add group"))))),0===o.length&&!n&&a.a.createElement(l.a,{onClick:this.onToggleAdding,buttonIcon:"users-alt",title:"There are no external groups to sync with",buttonTitle:"Add Group",proTip:y,proTipLinkTitle:"Learn more",proTipLink:"http://docs.grafana.org/auth/enhanced_ldap/",proTipTarget:"_blank"}),o.length>0&&a.a.createElement("div",{className:"admin-list-table"},a.a.createElement("table",{className:"filter-table filter-table--hover form-inline"},a.a.createElement("thead",null,a.a.createElement("tr",null,a.a.createElement("th",null,"External Group ID"),a.a.createElement("th",{style:{width:"1%"}}))),a.a.createElement("tbody",null,o.map((function(t){return e.renderGroup(t)}))))))}}])&&p(n.prototype,r),o&&p(n,o),t}(r.PureComponent);var E={loadTeamGroups:u.e,addTeamGroup:u.a,removeTeamGroup:u.h};t.a=Object(o.connect)((function(e){return{groups:Object(s.d)(e.team)}}),E)(v)},cwy8:function(e,t,n){"use strict";var r=n("q1tI"),a=n.n(r),o=n("/MKj"),i=n("kDLi"),c=n("BVom"),u=n("+dgx"),s=n("rCnR"),l=n("gxTa"),m=n("8uRs"),f=n("EKT6"),p=function(e){var t=e.featureToggle,n=e.children;return!0===t?a.a.createElement(a.a.Fragment,null,n):null},d=n("ZFWI"),b=n("umNM"),g=n("GQ3c");function h(e){return(h="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(e){return typeof e}:function(e){return e&&"function"==typeof Symbol&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e})(e)}function y(e,t){var n=Object.keys(e);if(Object.getOwnPropertySymbols){var r=Object.getOwnPropertySymbols(e);t&&(r=r.filter((function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable}))),n.push.apply(n,r)}return n}function v(e,t,n){return t in e?Object.defineProperty(e,t,{value:n,enumerable:!0,configurable:!0,writable:!0}):e[t]=n,e}function E(e,t){for(var n=0;n<t.length;n++){var r=t[n];r.enumerable=r.enumerable||!1,r.configurable=!0,"value"in r&&(r.writable=!0),Object.defineProperty(e,r.key,r)}}function w(e){return(w=Object.setPrototypeOf?Object.getPrototypeOf:function(e){return e.__proto__||Object.getPrototypeOf(e)})(e)}function O(e){if(void 0===e)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return e}function j(e,t){return(j=Object.setPrototypeOf||function(e,t){return e.__proto__=t,e})(e,t)}var T=i.LegacyForms.Select,S=function(e){function t(e){var n,r,a;return function(e,t){if(!(e instanceof t))throw new TypeError("Cannot call a class as a function")}(this,t),r=this,a=w(t).call(this,e),(n=!a||"object"!==h(a)&&"function"!=typeof a?O(r):a).onPermissionChange=function(e,t){var r=function(e){for(var t=1;t<arguments.length;t++){var n=null!=arguments[t]?arguments[t]:{};t%2?y(Object(n),!0).forEach((function(t){v(e,t,n[t])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(n)):y(Object(n)).forEach((function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(n,t))}))}return e}({},t,{permission:e.value});n.props.updateTeamMember(r)},n.renderLabels=n.renderLabels.bind(O(n)),n.renderPermissions=n.renderPermissions.bind(O(n)),n}var n,r,o;return function(e,t){if("function"!=typeof t&&null!==t)throw new TypeError("Super expression must either be null or a function");e.prototype=Object.create(t&&t.prototype,{constructor:{value:e,writable:!0,configurable:!0}}),t&&j(e,t)}(t,e),n=t,(r=[{key:"onRemoveMember",value:function(e){this.props.removeTeamMember(e.userId)}},{key:"renderPermissions",value:function(e){var t=this,n=this.props,r=n.editorsCanAdmin,o=n.signedInUserIsTeamAdmin,i=g.teamsPermissionLevels.find((function(t){return t.value===e.permission}));return a.a.createElement(p,{featureToggle:r},a.a.createElement("td",{className:"width-5 team-permissions"},a.a.createElement("div",{className:"gf-form"},o&&a.a.createElement(T,{isSearchable:!1,options:g.teamsPermissionLevels,onChange:function(n){return t.onPermissionChange(n,e)},className:"gf-form-select-box__control--menu-right",value:i}),!o&&a.a.createElement("span",null,i.label))))}},{key:"renderLabels",value:function(e){return e?a.a.createElement("td",null,e.map((function(e){return a.a.createElement(s.a,{key:e,label:e,removeIcon:!1,count:0,onClick:function(){}})}))):a.a.createElement("td",null)}},{key:"render",value:function(){var e=this,t=this.props,n=t.member,r=t.syncEnabled,o=t.signedInUserIsTeamAdmin;return a.a.createElement("tr",{key:n.userId},a.a.createElement("td",{className:"width-4 text-center"},a.a.createElement("img",{className:"filter-table__avatar",src:n.avatarUrl})),a.a.createElement("td",null,n.login),a.a.createElement("td",null,n.email),a.a.createElement("td",null,n.name),this.renderPermissions(n),r&&this.renderLabels(n.labels),a.a.createElement("td",{className:"text-right"},a.a.createElement(i.DeleteButton,{size:"sm",disabled:!o,onConfirm:function(){return e.onRemoveMember(n)}})))}}])&&E(n.prototype,r),o&&E(n,o),t}(r.PureComponent);var k={removeTeamMember:l.i,updateTeamMember:l.k},x=Object(o.connect)((function(e){return{}}),k)(S),P=n("BPIC");function I(e){return(I="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(e){return typeof e}:function(e){return e&&"function"==typeof Symbol&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e})(e)}function C(e,t,n,r,a,o,i){try{var c=e[o](i),u=c.value}catch(e){return void n(e)}c.done?t(u):Promise.resolve(u).then(r,a)}function N(e){return function(){var t=this,n=arguments;return new Promise((function(r,a){var o=e.apply(t,n);function i(e){C(o,r,a,i,c,"next",e)}function c(e){C(o,r,a,i,c,"throw",e)}i(void 0)}))}}function _(e,t){for(var n=0;n<t.length;n++){var r=t[n];r.enumerable=r.enumerable||!1,r.configurable=!0,"value"in r&&(r.writable=!0),Object.defineProperty(e,r.key,r)}}function A(e,t){return!t||"object"!==I(t)&&"function"!=typeof t?function(e){if(void 0===e)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return e}(e):t}function R(e){return(R=Object.setPrototypeOf?Object.getPrototypeOf:function(e){return e.__proto__||Object.getPrototypeOf(e)})(e)}function M(e,t){return(M=Object.setPrototypeOf||function(e,t){return e.__proto__=t,e})(e,t)}var G=function(e){function t(e){var n;return function(e,t){if(!(e instanceof t))throw new TypeError("Cannot call a class as a function")}(this,t),(n=A(this,R(t).call(this,e))).onSearchQueryChange=function(e){n.props.setSearchMemberQuery(e)},n.onToggleAdding=function(){n.setState({isAdding:!n.state.isAdding})},n.onUserSelected=function(e){n.setState({newTeamMember:e})},n.onAddUserToTeam=N(regeneratorRuntime.mark((function e(){return regeneratorRuntime.wrap((function(e){for(;;)switch(e.prev=e.next){case 0:n.props.addTeamMember(n.state.newTeamMember.id),n.setState({newTeamMember:null});case 2:case"end":return e.stop()}}),e)}))),n.state={isAdding:!1,newTeamMember:null},n}var n,r,o;return function(e,t){if("function"!=typeof t&&null!==t)throw new TypeError("Super expression must either be null or a function");e.prototype=Object.create(t&&t.prototype,{constructor:{value:e,writable:!0,configurable:!0}}),t&&M(e,t)}(t,e),n=t,(r=[{key:"renderLabels",value:function(e){return e?a.a.createElement("td",null,e.map((function(e){return a.a.createElement(s.a,{key:e,label:e,removeIcon:!1,count:0,onClick:function(){}})}))):a.a.createElement("td",null)}},{key:"render",value:function(){var e=this.state.isAdding,t=this.props,n=t.searchMemberQuery,r=t.members,o=t.syncEnabled,s=t.editorsCanAdmin,l=t.signedInUser,d=Object(m.i)({members:r,editorsCanAdmin:s,signedInUser:l});return a.a.createElement("div",null,a.a.createElement("div",{className:"page-action-bar"},a.a.createElement("div",{className:"gf-form gf-form--grow"},a.a.createElement(f.a,{labelClassName:"gf-form--has-input-icon gf-form--grow",inputClassName:"gf-form-input",placeholder:"Search members",value:n,onChange:this.onSearchQueryChange})),a.a.createElement("div",{className:"page-action-bar__spacer"}),a.a.createElement("button",{className:"btn btn-primary pull-right",onClick:this.onToggleAdding,disabled:e||!d},"Add member")),a.a.createElement(c.a,{in:e},a.a.createElement("div",{className:"cta-form"},a.a.createElement("button",{className:"cta-form__close btn btn-transparent",onClick:this.onToggleAdding},a.a.createElement(i.Icon,{name:"times"})),a.a.createElement("h5",null,"Add team member"),a.a.createElement("div",{className:"gf-form-inline"},a.a.createElement(u.a,{onSelected:this.onUserSelected,className:"min-width-30"}),this.state.newTeamMember&&a.a.createElement("button",{className:"btn btn-primary gf-form-btn",type:"submit",onClick:this.onAddUserToTeam},"Add to team")))),a.a.createElement("div",{className:"admin-list-table"},a.a.createElement("table",{className:"filter-table filter-table--hover form-inline"},a.a.createElement("thead",null,a.a.createElement("tr",null,a.a.createElement("th",null),a.a.createElement("th",null,"Login"),a.a.createElement("th",null,"Email"),a.a.createElement("th",null,"Name"),a.a.createElement(p,{featureToggle:s},a.a.createElement("th",null,"Permission")),o&&a.a.createElement("th",null),a.a.createElement("th",{style:{width:"1%"}}))),a.a.createElement("tbody",null,r&&r.map((function(e){return a.a.createElement(x,{key:e.userId,member:e,syncEnabled:o,editorsCanAdmin:s,signedInUserIsTeamAdmin:d})}))))))}}])&&_(n.prototype,r),o&&_(n,o),t}(r.PureComponent);var L={addTeamMember:l.b,setSearchMemberQuery:P.b};t.a=Object(o.connect)((function(e){return{searchMemberQuery:Object(m.a)(e.team),editorsCanAdmin:d.a.editorsCanAdmin,signedInUser:b.a.user}}),L)(G)},gxTa:function(e,t,n){"use strict";n.d(t,"g",(function(){return s})),n.d(t,"d",(function(){return l})),n.d(t,"f",(function(){return m})),n.d(t,"b",(function(){return f})),n.d(t,"i",(function(){return p})),n.d(t,"j",(function(){return d})),n.d(t,"e",(function(){return b})),n.d(t,"a",(function(){return g})),n.d(t,"h",(function(){return h})),n.d(t,"c",(function(){return y})),n.d(t,"k",(function(){return v}));var r=n("t8hP"),a=n("3SGO"),o=n("zsYB"),i=n("BPIC");function c(e,t,n,r,a,o,i){try{var c=e[o](i),u=c.value}catch(e){return void n(e)}c.done?t(u):Promise.resolve(u).then(r,a)}function u(e){return function(){var t=this,n=arguments;return new Promise((function(r,a){var o=e.apply(t,n);function i(e){c(o,r,a,i,u,"next",e)}function u(e){c(o,r,a,i,u,"throw",e)}i(void 0)}))}}function s(){return function(){var e=u(regeneratorRuntime.mark((function e(t){var n;return regeneratorRuntime.wrap((function(e){for(;;)switch(e.prev=e.next){case 0:return e.next=2,Object(r.getBackendSrv)().get("/api/teams/search",{perpage:1e3,page:1});case 2:n=e.sent,t(Object(i.g)(n.teams));case 4:case"end":return e.stop()}}),e)})));return function(t){return e.apply(this,arguments)}}()}function l(e){return function(){var t=u(regeneratorRuntime.mark((function t(n){var c;return regeneratorRuntime.wrap((function(t){for(;;)switch(t.prev=t.next){case 0:return t.next=2,Object(r.getBackendSrv)().get("/api/teams/".concat(e));case 2:c=t.sent,n(Object(i.e)(c)),n(Object(a.d)(Object(o.a)(c)));case 5:case"end":return t.stop()}}),t)})));return function(e){return t.apply(this,arguments)}}()}function m(){return function(){var e=u(regeneratorRuntime.mark((function e(t,n){var a,o;return regeneratorRuntime.wrap((function(e){for(;;)switch(e.prev=e.next){case 0:return a=n().team.team,e.next=3,Object(r.getBackendSrv)().get("/api/teams/".concat(a.id,"/members"));case 3:o=e.sent,t(Object(i.f)(o));case 5:case"end":return e.stop()}}),e)})));return function(t,n){return e.apply(this,arguments)}}()}function f(e){return function(){var t=u(regeneratorRuntime.mark((function t(n,a){var o;return regeneratorRuntime.wrap((function(t){for(;;)switch(t.prev=t.next){case 0:return o=a().team.team,t.next=3,Object(r.getBackendSrv)().post("/api/teams/".concat(o.id,"/members"),{userId:e});case 3:n(m());case 4:case"end":return t.stop()}}),t)})));return function(e,n){return t.apply(this,arguments)}}()}function p(e){return function(){var t=u(regeneratorRuntime.mark((function t(n,a){var o;return regeneratorRuntime.wrap((function(t){for(;;)switch(t.prev=t.next){case 0:return o=a().team.team,t.next=3,Object(r.getBackendSrv)().delete("/api/teams/".concat(o.id,"/members/").concat(e));case 3:n(m());case 4:case"end":return t.stop()}}),t)})));return function(e,n){return t.apply(this,arguments)}}()}function d(e,t){return function(){var n=u(regeneratorRuntime.mark((function n(a,o){var i;return regeneratorRuntime.wrap((function(n){for(;;)switch(n.prev=n.next){case 0:return i=o().team.team,n.next=3,Object(r.getBackendSrv)().put("/api/teams/".concat(i.id),{name:e,email:t});case 3:a(l(i.id));case 4:case"end":return n.stop()}}),n)})));return function(e,t){return n.apply(this,arguments)}}()}function b(){return function(){var e=u(regeneratorRuntime.mark((function e(t,n){var a,o;return regeneratorRuntime.wrap((function(e){for(;;)switch(e.prev=e.next){case 0:return a=n().team.team,e.next=3,Object(r.getBackendSrv)().get("/api/teams/".concat(a.id,"/groups"));case 3:o=e.sent,t(Object(i.d)(o));case 5:case"end":return e.stop()}}),e)})));return function(t,n){return e.apply(this,arguments)}}()}function g(e){return function(){var t=u(regeneratorRuntime.mark((function t(n,a){var o;return regeneratorRuntime.wrap((function(t){for(;;)switch(t.prev=t.next){case 0:return o=a().team.team,t.next=3,Object(r.getBackendSrv)().post("/api/teams/".concat(o.id,"/groups"),{groupId:e});case 3:n(b());case 4:case"end":return t.stop()}}),t)})));return function(e,n){return t.apply(this,arguments)}}()}function h(e){return function(){var t=u(regeneratorRuntime.mark((function t(n,a){var o;return regeneratorRuntime.wrap((function(t){for(;;)switch(t.prev=t.next){case 0:return o=a().team.team,t.next=3,Object(r.getBackendSrv)().delete("/api/teams/".concat(o.id,"/groups/").concat(encodeURIComponent(e)));case 3:n(b());case 4:case"end":return t.stop()}}),t)})));return function(e,n){return t.apply(this,arguments)}}()}function y(e){return function(){var t=u(regeneratorRuntime.mark((function t(n){return regeneratorRuntime.wrap((function(t){for(;;)switch(t.prev=t.next){case 0:return t.next=2,Object(r.getBackendSrv)().delete("/api/teams/".concat(e));case 2:n(s());case 3:case"end":return t.stop()}}),t)})));return function(e){return t.apply(this,arguments)}}()}function v(e){return function(){var t=u(regeneratorRuntime.mark((function t(n){return regeneratorRuntime.wrap((function(t){for(;;)switch(t.prev=t.next){case 0:return t.next=2,Object(r.getBackendSrv)().put("/api/teams/".concat(e.teamId,"/members/").concat(e.userId),{permission:e.permission});case 2:n(m());case 3:case"end":return t.stop()}}),t)})));return function(e){return t.apply(this,arguments)}}()}},"p+xb":function(e,t,n){"use strict";n.r(t),function(e){n.d(t,"TeamPages",(function(){return P}));var r,a=n("q1tI"),o=n.n(a),i=n("/MKj"),c=n("LvDl"),u=n.n(c),s=n("0cfB"),l=n("ZFWI"),m=n("ZGyg"),f=n("cwy8"),p=n("Rczg"),d=n("WB4m"),b=n("gxTa"),g=n("8uRs"),h=n("zsYB"),y=n("lzJ5"),v=n("X+V3"),E=n("umNM");function w(e){return(w="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(e){return typeof e}:function(e){return e&&"function"==typeof Symbol&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e})(e)}function O(e,t,n,r,a,o,i){try{var c=e[o](i),u=c.value}catch(e){return void n(e)}c.done?t(u):Promise.resolve(u).then(r,a)}function j(e){return function(){var t=this,n=arguments;return new Promise((function(r,a){var o=e.apply(t,n);function i(e){O(o,r,a,i,c,"next",e)}function c(e){O(o,r,a,i,c,"throw",e)}i(void 0)}))}}function T(e,t){for(var n=0;n<t.length;n++){var r=t[n];r.enumerable=r.enumerable||!1,r.configurable=!0,"value"in r&&(r.writable=!0),Object.defineProperty(e,r.key,r)}}function S(e,t){return!t||"object"!==w(t)&&"function"!=typeof t?function(e){if(void 0===e)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return e}(e):t}function k(e){return(k=Object.setPrototypeOf?Object.getPrototypeOf:function(e){return e.__proto__||Object.getPrototypeOf(e)})(e)}function x(e,t){return(x=Object.setPrototypeOf||function(e,t){return e.__proto__=t,e})(e,t)}!function(e){e.Members="members",e.Settings="settings",e.GroupSync="groupsync"}(r||(r={}));var P=function(e){function t(e){var n;return function(e,t){if(!(e instanceof t))throw new TypeError("Cannot call a class as a function")}(this,t),(n=S(this,k(t).call(this,e))).textsAreEqual=function(e,t){return!e&&!t||!(!e||!t)&&e.toLocaleLowerCase()===t.toLocaleLowerCase()},n.hideTabsFromNonTeamAdmin=function(e,t){return!t&&e.main&&e.main.children&&e.main.children.filter((function(e){return!n.textsAreEqual(e.text,r.Members)})).map((function(e){e.hideFromTabs=!0})),e},n.state={isLoading:!1,isSyncEnabled:l.b.licenseInfo.hasLicense},n}var n,a,i,c,s;return function(e,t){if("function"!=typeof t&&null!==t)throw new TypeError("Super expression must either be null or a function");e.prototype=Object.create(t&&t.prototype,{constructor:{value:e,writable:!0,configurable:!0}}),t&&x(e,t)}(t,e),n=t,(a=[{key:"componentDidMount",value:(s=j(regeneratorRuntime.mark((function e(){return regeneratorRuntime.wrap((function(e){for(;;)switch(e.prev=e.next){case 0:return e.next=2,this.fetchTeam();case 2:case"end":return e.stop()}}),e,this)}))),function(){return s.apply(this,arguments)})},{key:"fetchTeam",value:(c=j(regeneratorRuntime.mark((function e(){var t,n,r,a;return regeneratorRuntime.wrap((function(e){for(;;)switch(e.prev=e.next){case 0:return t=this.props,n=t.loadTeam,r=t.teamId,this.setState({isLoading:!0}),e.next=4,n(r);case 4:return a=e.sent,e.next=7,this.props.loadTeamMembers();case 7:return this.setState({isLoading:!1}),e.abrupt("return",a);case 9:case"end":return e.stop()}}),e,this)}))),function(){return c.apply(this,arguments)})},{key:"getCurrentPage",value:function(){var e=["members","settings","groupsync"],t=this.props.pageName;return u.a.includes(e,t)?t:e[0]}},{key:"renderPage",value:function(e){var t=this.state.isSyncEnabled,n=this.props.members;switch(this.getCurrentPage()){case r.Members:return o.a.createElement(f.a,{syncEnabled:t,members:n});case r.Settings:return e&&o.a.createElement(p.a,null);case r.GroupSync:return e&&t&&o.a.createElement(d.a,null)}return null}},{key:"render",value:function(){var e=this.props,t=e.team,n=e.navModel,r=e.members,a=e.editorsCanAdmin,i=e.signedInUser,c=Object(g.i)({members:r,editorsCanAdmin:a,signedInUser:i});return o.a.createElement(m.a,{navModel:this.hideTabsFromNonTeamAdmin(n,c)},o.a.createElement(m.a.Contents,{isLoading:this.state.isLoading},t&&0!==Object.keys(t).length&&this.renderPage(c)))}}])&&T(n.prototype,a),i&&T(n,i),t}(a.PureComponent);var I={loadTeam:b.d,loadTeamMembers:b.f};t.default=Object(s.hot)(e)(Object(i.connect)((function(e){var t=Object(v.c)(e.location),n=Object(v.d)(e.location)||"members",r=Object(h.b)(n);return{navModel:Object(y.a)(e.navIndex,"team-".concat(n,"-").concat(t),r),teamId:t,pageName:n,team:Object(g.c)(e.team,t),members:Object(g.e)(e.team),editorsCanAdmin:l.b.editorsCanAdmin,signedInUser:E.a.user}}),I)(P))}.call(this,n("3UD+")(e))},zsYB:function(e,t,n){"use strict";n.d(t,"a",(function(){return o})),n.d(t,"b",(function(){return i}));var r=n("GQ3c"),a=n("ZFWI");function o(e){var t={img:e.avatarUrl,id:"team-"+e.id,subTitle:"Manage members & settings",url:"",text:e.name,breadcrumbs:[{title:"Teams",url:"org/teams"}],children:[{active:!1,icon:"users-alt",id:"team-members-".concat(e.id),text:"Members",url:"org/teams/edit/".concat(e.id,"/members")},{active:!1,icon:"sliders-v-alt",id:"team-settings-".concat(e.id),text:"Settings",url:"org/teams/edit/".concat(e.id,"/settings")}]};return a.b.licenseInfo.hasLicense&&t.children.push({active:!1,icon:"sync",id:"team-groupsync-".concat(e.id),text:"External group sync",url:"org/teams/edit/".concat(e.id,"/groupsync")}),t}function i(e){var t,n=o({avatarUrl:"public/img/user_profile.png",id:1,name:"Loading",email:"loading",memberCount:0,permission:r.TeamPermissionLevel.Member}),a=!0,i=!1,c=void 0;try{for(var u,s=n.children[Symbol.iterator]();!(a=(u=s.next()).done);a=!0){var l=u.value;if(l.id.indexOf(e)>0){l.active=!0,t=l;break}}}catch(e){i=!0,c=e}finally{try{a||null==s.return||s.return()}finally{if(i)throw c}}return{main:n,node:t}}}}]);
//# sourceMappingURL=TeamPages.017a0d1a58b1119d038d.js.map