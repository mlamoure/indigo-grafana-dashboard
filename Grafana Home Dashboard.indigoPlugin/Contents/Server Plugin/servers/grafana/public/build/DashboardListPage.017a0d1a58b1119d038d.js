(window.webpackJsonp=window.webpackJsonp||[]).push([[13],{Kwub:function(e,n,r){"use strict";r.d(n,"a",(function(){return o}));var t=r("q1tI"),a=r("VQUf");function o(e,n,r){void 0===n&&(n=[]),void 0===r&&(r={loading:!1});var o=Object(t.useRef)(0),i=Object(t.useState)(r),c=i[0],u=i[1],s=Object(a.a)();return[c,Object(t.useCallback)((function(){for(var n=[],r=0;r<arguments.length;r++)n[r]=arguments[r];var t=++o.current;return u({loading:!0}),e.apply(void 0,n).then((function(e){return s()&&t===o.current&&u({value:e,loading:!1}),e}),(function(e){return s()&&t===o.current&&u({error:e,loading:!1}),e}))}),n)]}},VQUf:function(e,n,r){"use strict";r.d(n,"a",(function(){return a}));var t=r("q1tI");function a(){var e=Object(t.useRef)(!1),n=Object(t.useCallback)((function(){return e.current}),[]);return Object(t.useEffect)((function(){return e.current=!0,function(){e.current=!1}})),n}},Y8YH:function(e,n,r){"use strict";r.d(n,"a",(function(){return o}));var t=r("q1tI"),a=r("Kwub");function o(e,n){void 0===n&&(n=[]);var r=Object(a.a)(e,n,{loading:!0}),o=r[0],i=r[1];return Object(t.useEffect)((function(){i()}),[i]),o}},zD1S:function(e,n,r){"use strict";r.r(n);var t=r("q1tI"),a=r.n(t),o=r("Y8YH"),i=r("/MKj"),c=r("Obii"),u=r("t8hP"),s=r("lzJ5"),d=r("X+V3"),l=r("ZGyg"),f=r("NXk7"),b=r("jbKi");function g(e,n){var r=Object.keys(e);if(Object.getOwnPropertySymbols){var t=Object.getOwnPropertySymbols(e);n&&(t=t.filter((function(n){return Object.getOwnPropertyDescriptor(e,n).enumerable}))),r.push.apply(r,t)}return r}function m(e){for(var n=1;n<arguments.length;n++){var r=null!=arguments[n]?arguments[n]:{};n%2?g(Object(r),!0).forEach((function(n){v(e,n,r[n])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(r)):g(Object(r)).forEach((function(n){Object.defineProperty(e,n,Object.getOwnPropertyDescriptor(r,n))}))}return e}function v(e,n,r){return n in e?Object.defineProperty(e,n,{value:r,enumerable:!0,configurable:!0,writable:!0}):e[n]=r,e}r.d(n,"DashboardListPage",(function(){return p}));var p=Object(t.memo)((function(e){var n=e.navModel,r=e.uid,t=e.url,i=Object(o.a)((function(){return r&&t.startsWith("/dashboards")?function(e,n){var r={main:{icon:"folder-open",id:"manage-folder",subTitle:"Manage folder dashboards & permissions",url:"",text:"",breadcrumbs:[{title:"Dashboards",url:"dashboards"}],children:[{active:"manage-folder-dashboards"===n,icon:"th-large",id:"manage-folder-dashboards",text:"Dashboards",url:"dashboards"},{active:"manage-folder-permissions"===n,icon:"lock",id:"manage-folder-permissions",text:"Permissions",url:"dashboards/permissions"},{active:"manage-folder-settings"===n,icon:"cog",id:"manage-folder-settings",text:"Settings",url:"dashboards/settings"}]}};return f.b.getFolderByUid(e).then((function(e){var n=e.title,t=e.url;r.main.text=n;var a=r.main.children.find((function(e){return"manage-folder-dashboards"===e.id}));(a.url=t,e.canAdmin)?(r.main.children.find((function(e){return"manage-folder-permissions"===e.id})).url=t+"/permissions",r.main.children.find((function(e){return"manage-folder-settings"===e.id})).url=t+"/settings"):r.main.children=[a];return{folder:e,model:r}}))}(r,"manage-folder-dashboards").then((function(e){var r=e.folder,t=e.model,a=c.locationUtil.stripBaseFromUrl(r.url);return a!==location.pathname&&Object(u.getLocationSrv)().update({path:a}),{folder:r,pageNavModel:m({},n,{},t)}})):Promise.resolve({pageNavModel:n})}),[r]),s=i.loading,d=i.value;return a.a.createElement(l.a,{navModel:null==d?void 0:d.pageNavModel},a.a.createElement(l.a.Contents,{isLoading:s},a.a.createElement(b.a,{folder:null==d?void 0:d.folder})))}));n.default=Object(i.connect)((function(e){return{navModel:Object(s.a)(e.navIndex,"manage-dashboards"),uid:Object(d.b)(e.location).uid,url:Object(d.e)(e.location)}}))(p)}}]);
//# sourceMappingURL=DashboardListPage.017a0d1a58b1119d038d.js.map