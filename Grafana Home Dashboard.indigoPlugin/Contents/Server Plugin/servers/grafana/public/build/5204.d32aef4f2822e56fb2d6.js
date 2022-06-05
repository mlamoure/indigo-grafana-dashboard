"use strict";(self.webpackChunkgrafana=self.webpackChunkgrafana||[]).push([[5204],{"./public/app/features/explore/AddToDashboard/index.tsx":(e,a,r)=>{r.r(a),r.d(a,{AddToDashboard:()=>A});var s=r("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js"),o=r("./.yarn/__virtual__/react-redux-virtual-7ad20a440e/3/opt/drone/yarncache/react-redux-npm-7.2.6-134f5ed64d-0bf142ce0d.zip/node_modules/react-redux/es/index.js"),t=r("./packages/grafana-ui/src/index.ts"),n=r("./public/app/features/explore/state/selectors.ts"),d=r("../../opt/drone/yarncache/lodash-npm-4.17.21-6382451519-eb835a2e51.zip/node_modules/lodash/lodash.js"),i=r("./.yarn/__virtual__/react-hook-form-virtual-92b6119fd4/3/opt/drone/yarncache/react-hook-form-npm-7.5.3-f9cc466c62-fbfaa3b664.zip/node_modules/react-hook-form/dist/index.esm.js"),l=r("./packages/grafana-data/src/index.ts"),c=r("./packages/grafana-runtime/src/index.ts"),u=r("./public/app/core/components/Select/DashboardPicker.tsx"),h=r("./public/app/features/dashboard/state/initDashboard.ts"),p=r("./public/app/core/services/backend_srv.ts");let b;async function f(e){var a;const r=function(e,a){for(const{refId:r}of e.filter(g)){const e=v(r);if(a.graphFrames.some(e))return"timeseries";if(a.logsFrames.some(e))return"logs";if(a.nodeGraphFrames.some(e))return"nodeGraph"}return"table"}(e.queries,e.queryResponse),s={targets:e.queries,type:r,title:"New Panel",gridPos:{x:0,y:0,w:12,h:8},datasource:e.datasource};let o;if(e.dashboardUid)try{o=await p.ae.getDashboardByUid(e.dashboardUid)}catch(e){throw b.FETCH_DASHBOARD}else o=function(){const e=(0,h.ZQ)();return e.dashboard.panels=[],e}();o.dashboard.panels=[s,...null!==(a=o.dashboard.panels)&&void 0!==a?a:[]];try{(0,h.$M)(o)}catch{throw b.SET_DASHBOARD_LS}}!function(e){e.FETCH_DASHBOARD="fetch-dashboard",e.SET_DASHBOARD_LS="set-dashboard-ls-error"}(b||(b={}));const g=e=>!e.hide,v=e=>a=>a.refId===e;var m=r("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");const x=["ref"],y=["ref","value","onChange"];function D(e,a){if(null==e)return{};var r,s,o={},t=Object.keys(e);for(s=0;s<t.length;s++)r=t[s],a.indexOf(r)>=0||(o[r]=e[r]);return o}var _;!function(e){e.NewDashboard="new-dashboard",e.ExistingDashboard="existing-dashboard"}(_||(_={}));const j=[{label:"New dashboard",value:_.NewDashboard},{label:"Existing dashboard",value:_.ExistingDashboard}];var w;!function(e){e.UNKNOWN="unknown-error",e.NAVIGATION="navigation-error"}(w||(w={}));const k=e=>{let{onClose:a,exploreId:p}=e;const g=(0,o.useSelector)((0,n.F)(p)),[v,k]=(0,s.useState)(),{handleSubmit:A,control:S,formState:{errors:C},watch:T}=(0,i.cI)({defaultValues:{saveTarget:_.NewDashboard}}),O=T("saveTarget"),I=async(e,s)=>{k(void 0);const o=s.saveTarget===_.ExistingDashboard?s.dashboardUid:void 0;(0,c.reportInteraction)("e2d_submit",{newTab:e,saveTarget:s.saveTarget,queries:g.queries.length});try{var t;await f({dashboardUid:o,datasource:null===(t=g.datasourceInstance)||void 0===t?void 0:t.getRef(),queries:g.queries,queryResponse:g.queryResponse})}catch(e){switch(e){case b.FETCH_DASHBOARD:k({error:e,message:"Could not fetch dashboard information. Please try again."});break;case b.SET_DASHBOARD_LS:k({error:e,message:"Could not add panel to dashboard. Please try again."});break;default:k({error:w.UNKNOWN,message:"Something went wrong. Please try again."})}return}const n=function(e){return e?`d/${e}`:"dashboard/new"}(o);if(!e)return a(),void c.locationService.push(l.locationUtil.stripBaseFromUrl(n));if(!!!r.g.open(c.config.appUrl+n,"_blank"))return k({error:w.NAVIGATION,message:"Could not navigate to the selected dashboard. Please try again."}),void(0,h.f1)();a()};return(0,s.useEffect)((()=>{(0,c.reportInteraction)("e2d_open")}),[]),(0,m.jsx)(t.Modal,{title:"Add panel to dashboard",onDismiss:a,isOpen:!0,children:(0,m.jsxs)("form",{children:[(0,m.jsx)(t.InputControl,{control:S,render:e=>{let{}=e,a=D(e.field,x);return(0,m.jsx)(t.Field,{label:"Target dashboard",description:"Choose where to add the panel.",children:(0,m.jsx)(t.RadioButtonGroup,Object.assign({options:j},a,{id:"e2d-save-target"}))})},name:"saveTarget"}),O===_.ExistingDashboard&&(0,m.jsx)(t.InputControl,{render:e=>{var a;let{field:{onChange:r}}=e,s=D(e.field,y);return(0,m.jsx)(t.Field,{label:"Dashboard",description:"Select in which dashboard the panel will be created.",error:null===(a=C.dashboardUid)||void 0===a?void 0:a.message,invalid:!!C.dashboardUid,children:(0,m.jsx)(u.o,Object.assign({},s,{inputId:"e2d-dashboard-picker",defaultOptions:!0,onChange:e=>r(null==e?void 0:e.uid)}))})},control:S,name:"dashboardUid",shouldUnregister:!0,rules:{required:{value:!0,message:"This field is required."}}}),v&&(0,m.jsx)(t.Alert,{severity:"error",title:"Error adding the panel",children:v.message}),(0,m.jsxs)(t.Modal.ButtonRow,{children:[(0,m.jsx)(t.Button,{type:"reset",onClick:a,fill:"outline",variant:"secondary",children:"Cancel"}),(0,m.jsx)(t.Button,{type:"submit",variant:"secondary",onClick:A((0,d.partial)(I,!0)),icon:"external-link-alt",children:"Open in new tab"}),(0,m.jsx)(t.Button,{type:"submit",variant:"primary",onClick:A((0,d.partial)(I,!1)),icon:"apps",children:"Open dashboard"})]})]})})},A=e=>{var a,r;let{exploreId:d}=e;const[i,l]=(0,s.useState)(!1),c=(0,n.F)(d),u=!(null===(a=(0,o.useSelector)(c))||void 0===a||null===(r=a.queries)||void 0===r||!r.length);return(0,m.jsxs)(m.Fragment,{children:[(0,m.jsx)(t.ToolbarButton,{icon:"apps",onClick:()=>l(!0),"aria-label":"Add to dashboard",disabled:!u,children:"Add to dashboard"}),i&&(0,m.jsx)(k,{onClose:()=>l(!1),exploreId:d})]})}}}]);
//# sourceMappingURL=5204.d32aef4f2822e56fb2d6.js.map