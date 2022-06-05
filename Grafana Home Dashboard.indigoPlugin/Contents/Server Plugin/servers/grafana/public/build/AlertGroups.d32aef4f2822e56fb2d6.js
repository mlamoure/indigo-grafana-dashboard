"use strict";(self.webpackChunkgrafana=self.webpackChunkgrafana||[]).push([[2415],{"./public/app/features/alerting/unified/AlertGroups.tsx":(e,a,t)=>{t.r(a),t.d(a,{default:()=>Y});var s=t("./.yarn/__virtual__/@emotion-css-virtual-72c314ddb1/3/opt/drone/yarncache/@emotion-css-npm-11.7.1-25ff8755a7-ac1f56656f.zip/node_modules/@emotion/css/dist/emotion-css.esm.js"),r=t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js"),n=t("./.yarn/__virtual__/react-redux-virtual-7ad20a440e/3/opt/drone/yarncache/react-redux-npm-7.2.6-134f5ed64d-0bf142ce0d.zip/node_modules/react-redux/es/index.js"),i=t("./packages/grafana-ui/src/index.ts"),l=t("./public/app/core/hooks/useQueryParams.ts"),c=t("./public/app/features/alerting/unified/components/AlertingPageWrapper.tsx"),o=t("./public/app/features/alerting/unified/components/NoAlertManagerWarning.tsx"),u=t("./public/app/plugins/datasource/alertmanager/types.ts"),p=t("./public/app/features/alerting/unified/components/AlertLabels.tsx"),d=t("./public/app/features/alerting/unified/components/CollapseToggle.tsx"),g=t("./packages/grafana-data/src/index.ts"),m=t("./public/app/features/alerting/unified/components/DynamicTableWithGuidelines.tsx"),b=t("./public/app/features/alerting/unified/components/silences/AmAlertStateTag.tsx"),f=t("./public/app/core/services/context_srv.ts"),x=t("./public/app/types/index.ts"),h=t("./public/app/features/alerting/unified/utils/access-control.ts"),j=t("./public/app/features/alerting/unified/utils/datasource.ts"),y=t("./public/app/features/alerting/unified/utils/misc.ts"),v=t("./public/app/features/alerting/unified/components/AnnotationDetailsField.tsx"),S=t("./public/app/features/alerting/unified/components/Authorize.tsx"),_=t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");const k=e=>{let{alert:a,alertManagerSourceName:t}=e;const s=(0,i.useStyles2)(N),r=(0,h.QX)(t),n=!(0,j.HY)(t)||f.Vt.hasPermission(x.bW.AlertingRuleRead);return(0,_.jsxs)(_.Fragment,{children:[(0,_.jsxs)("div",{className:s.actionsRow,children:[(0,_.jsxs)(S.q,{actions:[r.update,r.create],fallback:f.Vt.isEditor,children:[a.status.state===u.Z9.Suppressed&&(0,_.jsx)(i.LinkButton,{href:`${(0,y.eQ)("/alerting/silences",t)}&silenceIds=${a.status.silencedBy.join(",")}`,className:s.button,icon:"bell",size:"sm",children:"Manage silences"}),a.status.state===u.Z9.Active&&(0,_.jsx)(i.LinkButton,{href:(0,y.VN)(t,a.labels),className:s.button,icon:"bell-slash",size:"sm",children:"Silence"})]}),n&&a.generatorURL&&(0,_.jsx)(i.LinkButton,{className:s.button,href:a.generatorURL,icon:"chart-line",size:"sm",children:"See source"})]}),Object.entries(a.annotations).map((e=>{let[a,t]=e;return(0,_.jsx)(v.a,{annotationKey:a,value:t},a)})),(0,_.jsxs)("div",{className:s.receivers,children:["Receivers:"," ",a.receivers.map((e=>{let{name:a}=e;return a})).filter((e=>!!e)).join(", ")]})]})},N=e=>({button:s.css`
    & + & {
      margin-left: ${e.spacing(1)};
    }
  `,actionsRow:s.css`
    padding: ${e.spacing(2,0)} !important;
    border-bottom: 1px solid ${e.colors.border.medium};
  `,receivers:s.css`
    padding: ${e.spacing(1,0)};
  `}),A=e=>{let{alerts:a,alertManagerSourceName:t}=e;const s=(0,i.useStyles2)(C),n=(0,r.useMemo)((()=>[{id:"state",label:"State",renderCell:e=>{let{data:a}=e;return(0,_.jsxs)(_.Fragment,{children:[(0,_.jsx)(b.G,{state:a.status.state}),(0,_.jsxs)("span",{className:s.duration,children:["for"," ",(0,g.intervalToAbbreviatedDurationString)({start:new Date(a.startsAt),end:new Date(a.endsAt)})]})]})},size:"220px"},{id:"labels",label:"Labels",renderCell:e=>{let{data:{labels:a}}=e;return(0,_.jsx)(p.s,{className:s.labels,labels:a})},size:1}]),[s]),l=(0,r.useMemo)((()=>a.map((e=>({id:e.fingerprint,data:e})))),[a]);return(0,_.jsx)("div",{className:s.tableWrapper,"data-testid":"alert-group-table",children:(0,_.jsx)(m.F,{cols:n,items:l,isExpandable:!0,renderExpandedContent:e=>{let{data:a}=e;return(0,_.jsx)(k,{alert:a,alertManagerSourceName:t})}})})},C=e=>({tableWrapper:s.css`
    margin-top: ${e.spacing(3)};
    ${e.breakpoints.up("md")} {
      margin-left: ${e.spacing(4.5)};
    }
  `,duration:s.css`
    margin-left: ${e.spacing(1)};
    font-size: ${e.typography.bodySmall.fontSize};
  `,labels:s.css`
    padding-bottom: 0;
  `});var z,M=t("./public/app/features/alerting/unified/components/alert-groups/AlertGroupHeader.tsx");const $=e=>{let{alertManagerSourceName:a,group:t}=e;const[s,n]=(0,r.useState)(!0),l=(0,i.useStyles2)(w);return(0,_.jsxs)("div",{className:l.wrapper,children:[(0,_.jsxs)("div",{className:l.header,children:[(0,_.jsxs)("div",{className:l.group,"data-testid":"alert-group",children:[(0,_.jsx)(d.U,{isCollapsed:s,onToggle:()=>n(!s),"data-testid":"alert-group-collapse-toggle"}),Object.keys(t.labels).length?(0,_.jsx)(p.s,{className:l.headerLabels,labels:t.labels}):z||(z=(0,_.jsx)("span",{children:"No grouping"}))]}),(0,_.jsx)(M.Z,{group:t})]}),!s&&(0,_.jsx)(A,{alertManagerSourceName:a,alerts:t.alerts})]})},w=e=>({wrapper:s.css`
    & + & {
      margin-top: ${e.spacing(2)};
    }
  `,headerLabels:s.css`
    padding-bottom: 0 !important;
    margin-bottom: -${e.spacing(.5)};
  `,header:s.css`
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    padding: ${e.spacing(1,1,1,0)};
    background-color: ${e.colors.background.secondary};
    width: 100%;
  `,group:s.css`
    display: flex;
    flex-direction: row;
    align-items: center;
  `,summary:s.css``,spanElement:s.css`
    margin-left: ${e.spacing(.5)};
  `,[u.Z9.Active]:s.css`
    color: ${e.colors.error.main};
  `,[u.Z9.Suppressed]:s.css`
    color: ${e.colors.primary.main};
  `,[u.Z9.Unprocessed]:s.css`
    color: ${e.colors.secondary.main};
  `});var G,O=t("./public/app/features/alerting/unified/hooks/useAlertManagerSourceName.ts"),F=t("./public/app/features/alerting/unified/hooks/useAlertManagerSources.ts"),B=t("./public/app/features/alerting/unified/components/AlertManagerPicker.tsx");const L=e=>{let{onStateFilterChange:a,stateFilter:t}=e;const s=(0,i.useStyles2)(I),r=Object.entries(u.Z9).sort(((e,a)=>{let[t]=e,[s]=a;return t<s?-1:1})).map((e=>{let[a,t]=e;return{label:a,value:t}}));return(0,_.jsxs)("div",{className:s.wrapper,children:[G||(G=(0,_.jsx)(i.Label,{children:"State"})),(0,_.jsx)(i.RadioButtonGroup,{options:r,value:t,onChange:a})]})},I=e=>({wrapper:s.css`
    margin-left: ${e.spacing(1)};
  `});var Z,P,W=t("../../opt/drone/yarncache/lodash-npm-4.17.21-6382451519-eb835a2e51.zip/node_modules/lodash/lodash.js");const E=e=>{let{className:a,groups:t,groupBy:s,onGroupingChange:r}=e;const n=(0,W.uniq)(t.flatMap((e=>e.alerts)).flatMap((e=>{let{labels:a}=e;return Object.keys(a)}))).filter((e=>!(e.startsWith("__")&&e.endsWith("__")))).map((e=>({label:e,value:e})));return(0,_.jsxs)("div",{"data-testid":"group-by-container",className:a,children:[Z||(Z=(0,_.jsx)(i.Label,{children:"Custom group by"})),(0,_.jsx)(i.MultiSelect,{"aria-label":"group by label keys",value:s,placeholder:"Group by",prefix:P||(P=(0,_.jsx)(i.Icon,{name:"tag-alt"})),onChange:e=>{r(e.map((e=>{let{value:a}=e;return a})))},options:n,menuShouldPortal:!0})]})};var q=t("./public/app/features/alerting/unified/components/alert-groups/MatcherFilter.tsx");const T=e=>{let{groups:a}=e;const[t,s]=(0,r.useState)(Math.floor(100*Math.random())),[n,c]=(0,l.K)(),{groupBy:o=[],queryString:u,alertState:p}=(0,y.lC)(n),d=`matcher-${t}`,g=(0,F.k)("instance"),[m,b]=(0,O.k)(g),f=(0,i.useStyles2)(D),x=!!(o.length>0||u||p);return(0,_.jsxs)("div",{className:f.wrapper,children:[(0,_.jsx)(B.P,{current:m,onChange:b,dataSources:g}),(0,_.jsxs)("div",{className:f.filterSection,children:[(0,_.jsx)(q.F,{className:f.filterInput,defaultQueryString:u,onFilterChange:e=>c({queryString:e||null})},d),(0,_.jsx)(E,{className:f.filterInput,groups:a,groupBy:o,onGroupingChange:e=>c({groupBy:e.length?e.join(","):null})}),(0,_.jsx)(L,{stateFilter:p,onStateFilterChange:e=>c({alertState:e||null})}),x&&(0,_.jsx)(i.Button,{className:f.clearButton,variant:"secondary",icon:"times",onClick:()=>{c({groupBy:null,queryString:null,alertState:null}),setTimeout((()=>s(t+1)),100)},children:"Clear filters"})]})]})},D=e=>({wrapper:s.css`
    border-bottom: 1px solid ${e.colors.border.medium};
    margin-bottom: ${e.spacing(3)};
  `,filterSection:s.css`
    display: flex;
    flex-direction: row;
    margin-bottom: ${e.spacing(3)};
  `,filterInput:s.css`
    width: 340px;
    & + & {
      margin-left: ${e.spacing(1)};
    }
  `,clearButton:s.css`
    margin-left: ${e.spacing(1)};
    margin-top: 19px;
  `});var R=t("./public/app/features/alerting/unified/utils/alertmanager.ts");var U,Q,K=t("./public/app/features/alerting/unified/hooks/useUnifiedAlertingSelector.ts"),V=t("./public/app/features/alerting/unified/state/actions.ts"),J=t("./public/app/features/alerting/unified/utils/constants.ts"),H=t("./public/app/features/alerting/unified/utils/redux.ts");const X=e=>({groupingBanner:s.css`
    margin: ${e.spacing(2,0)};
  `}),Y=()=>{var e;const a=(0,F.k)("instance"),[t]=(0,O.k)(a),s=(0,n.useDispatch)(),[u]=(0,l.K)(),{groupBy:p=[]}=(0,y.lC)(u),d=(0,i.useStyles2)(X),g=(0,K._)((e=>e.amAlertGroups)),{loading:m,error:b,result:f=[]}=null!==(e=g[t||""])&&void 0!==e?e:H.oq,x=((e,a)=>(0,r.useMemo)((()=>0===a.length?e.filter((e=>0===Object.keys(e.labels).length)).length>1?e.reduce(((e,a)=>{if(0===Object.keys(a.labels).length){const t=e.find((e=>{let{labels:a}=e;return Object.keys(a)}));t?t.alerts=(0,W.uniqBy)([...t.alerts,...a.alerts],"labels"):e.push({alerts:a.alerts,labels:{},receiver:{name:"NONE"}})}else e.push(a);return e}),[]):e:e.flatMap((e=>{let{alerts:a}=e;return a})).reduce(((e,t)=>{if(a.every((e=>Object.keys(t.labels).includes(e)))){const s=e.find((e=>a.every((a=>e.labels[a]===t.labels[a]))));if(s)s.alerts.push(t);else{const s=a.reduce(((e,a)=>Object.assign({},e,{[a]:t.labels[a]})),{});e.push({alerts:[t],labels:s,receiver:{name:"NONE"}})}}else{const a=e.find((e=>0===Object.keys(e.labels).length));a?a.alerts.push(t):e.push({alerts:[t],labels:{},receiver:{name:"NONE"}})}return e}),[])),[e,a]))(f,p),h=(e=>{const[a]=(0,l.K)(),t=(0,y.lC)(a),s=(0,R.Zh)(t.queryString||"");return(0,r.useMemo)((()=>e.reduce(((e,a)=>{const r=a.alerts.filter((e=>{let{labels:a,status:r}=e;const n=(0,R.eD)(a,s),i=!t.alertState||r.state===t.alertState;return n&&i}));return r.length>0&&(0===Object.keys(a.labels).length?e.unshift(Object.assign({},a,{alerts:r})):e.push(Object.assign({},a,{alerts:r}))),e}),[])),[e,t,s])})(x);return(0,r.useEffect)((()=>{function e(){t&&s((0,V.mS)(t))}e();const a=setInterval(e,J.iF);return()=>{clearInterval(a)}}),[s,t]),t?(0,_.jsxs)(c.J,{pageId:"groups",children:[(0,_.jsx)(T,{groups:f}),m&&(U||(U=(0,_.jsx)(i.LoadingPlaceholder,{text:"Loading notifications"}))),b&&!m&&(0,_.jsx)(i.Alert,{title:"Error loading notifications",severity:"error",children:b.message||"Unknown error"}),f&&h.map(((e,a)=>(0,_.jsxs)(r.Fragment,{children:[(1===a&&0===Object.keys(h[0].labels).length||0===a&&Object.keys(e.labels).length>0)&&(0,_.jsxs)("p",{className:d.groupingBanner,children:["Grouped by: ",Object.keys(e.labels).join(", ")]}),(0,_.jsx)($,{alertManagerSourceName:t||"",group:e})]},`${JSON.stringify(e.labels)}-group-${a}`))),f&&!h.length&&(Q||(Q=(0,_.jsx)("p",{children:"No results."})))]}):(0,_.jsx)(c.J,{pageId:"groups",children:(0,_.jsx)(o.I,{availableAlertManagers:a})})}},"./public/app/features/alerting/unified/components/AlertingPageWrapper.tsx":(e,a,t)=>{t.d(a,{J:()=>l});t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js");var s=t("./.yarn/__virtual__/react-redux-virtual-7ad20a440e/3/opt/drone/yarncache/react-redux-npm-7.2.6-134f5ed64d-0bf142ce0d.zip/node_modules/react-redux/es/index.js"),r=t("./public/app/core/components/Page/Page.tsx"),n=t("./public/app/core/selectors/navModel.ts"),i=t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");const l=e=>{let{children:a,pageId:t,isLoading:l}=e;const c=(0,n.h)((0,s.useSelector)((e=>e.navIndex)),t);return(0,i.jsx)(r.Z,{navModel:c,children:(0,i.jsx)(r.Z.Contents,{isLoading:l,children:a})})}},"./public/app/features/alerting/unified/components/Authorize.tsx":(e,a,t)=>{t.d(a,{q:()=>n});t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js");var s=t("./public/app/core/services/context_srv.ts"),r=t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");const n=e=>{let{actions:a,children:t,fallback:n=!0}=e;return a.some((e=>s.Vt.hasAccess(e,n)))?(0,r.jsx)(r.Fragment,{children:t}):null}},"./public/app/features/alerting/unified/components/DynamicTableWithGuidelines.tsx":(e,a,t)=>{t.d(a,{F:()=>c});var s=t("./.yarn/__virtual__/@emotion-css-virtual-72c314ddb1/3/opt/drone/yarncache/@emotion-css-npm-11.7.1-25ff8755a7-ac1f56656f.zip/node_modules/@emotion/css/dist/emotion-css.esm.js"),r=(t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js"),t("./packages/grafana-ui/src/index.ts")),n=t("./public/app/features/alerting/unified/components/DynamicTable.tsx"),i=t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");const l=["renderExpandedContent"];const c=e=>{let{renderExpandedContent:a}=e,t=function(e,a){if(null==e)return{};var t,s,r={},n=Object.keys(e);for(s=0;s<n.length;s++)t=n[s],a.indexOf(t)>=0||(r[t]=e[t]);return r}(e,l);const c=(0,r.useStyles2)(o);return(0,i.jsx)(n.t,Object.assign({renderExpandedContent:a?(e,t,r)=>(0,i.jsxs)(i.Fragment,{children:[!(t===r.length-1)&&(0,i.jsx)("div",{className:(0,s.cx)(c.contentGuideline,c.guideline)}),a(e,t,r)]}):void 0,renderPrefixHeader:()=>(0,i.jsx)("div",{className:c.relative,children:(0,i.jsx)("div",{className:(0,s.cx)(c.headerGuideline,c.guideline)})}),renderPrefixCell:(e,a,t)=>(0,i.jsxs)("div",{className:c.relative,children:[(0,i.jsx)("div",{className:(0,s.cx)(c.topGuideline,c.guideline)}),!(a===t.length-1)&&(0,i.jsx)("div",{className:(0,s.cx)(c.bottomGuideline,c.guideline)})]})},t))},o=e=>({relative:s.css`
    position: relative;
    height: 100%;
  `,guideline:s.css`
    left: -19px;
    border-left: 1px solid ${e.colors.border.medium};
    position: absolute;

    ${e.breakpoints.down("md")} {
      display: none;
    }
  `,topGuideline:s.css`
    width: 18px;
    border-bottom: 1px solid ${e.colors.border.medium};
    top: 0;
    bottom: 50%;
  `,bottomGuideline:s.css`
    top: 50%;
    bottom: 0;
  `,contentGuideline:s.css`
    top: 0;
    bottom: 0;
    left: -49px !important;
  `,headerGuideline:s.css`
    top: -25px;
    bottom: 0;
  `})},"./public/app/features/alerting/unified/components/NoAlertManagerWarning.tsx":(e,a,t)=>{t.d(a,{I:()=>g});t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js");var s,r,n,i,l=t("./packages/grafana-ui/src/index.ts"),c=t("./public/app/features/alerting/unified/hooks/useAlertManagerSourceName.ts"),o=t("./public/app/features/alerting/unified/components/AlertManagerPicker.tsx"),u=t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");const p=()=>s||(s=(0,u.jsx)(l.Alert,{title:"No Alertmanager found",severity:"warning",children:"We could not find any external Alertmanagers and you may not have access to the built-in Grafana Alertmanager."})),d=()=>r||(r=(0,u.jsx)(l.Alert,{title:"Selected Alertmanager not found. Select a different Alertmanager.",severity:"warning",children:"Selected Alertmanager no longer exists or you may not have permission to access it."})),g=e=>{let{availableAlertManagers:a}=e;const[t,s]=(0,c.k)(a),r=a.length>0;return(0,u.jsx)("div",{children:r?(0,u.jsxs)(u.Fragment,{children:[(0,u.jsx)(o.P,{onChange:s,dataSources:a}),n||(n=(0,u.jsx)(d,{}))]}):i||(i=(0,u.jsx)(p,{}))})}},"./public/app/features/alerting/unified/components/alert-groups/MatcherFilter.tsx":(e,a,t)=>{t.d(a,{F:()=>u});var s,r,n,i=t("./.yarn/__virtual__/@emotion-css-virtual-72c314ddb1/3/opt/drone/yarncache/@emotion-css-npm-11.7.1-25ff8755a7-ac1f56656f.zip/node_modules/@emotion/css/dist/emotion-css.esm.js"),l=(t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js"),t("./.yarn/__virtual__/@grafana-experimental-virtual-920bad95a1/3/opt/drone/yarncache/@grafana-experimental-npm-0.0.2-canary.22-45d2c4f135-b9a64c0abc.zip/node_modules/@grafana/experimental/index.js")),c=t("./packages/grafana-ui/src/index.ts"),o=t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");const u=e=>{let{className:a,onFilterChange:t,defaultQueryString:i,queryString:u}=e;const d=(0,c.useStyles2)(p),g=s||(s=(0,o.jsx)(c.Icon,{name:"search"}));return(0,o.jsxs)("div",{className:a,children:[(0,o.jsx)(c.Label,{children:(0,o.jsxs)(l.Stack,{gap:.5,children:[r||(r=(0,o.jsx)("span",{children:"Search by label"})),(0,o.jsx)(c.Tooltip,{content:n||(n=(0,o.jsxs)("div",{children:["Filter alerts using label querying, ex:",(0,o.jsx)("pre",{children:'{severity="critical", instance=~"cluster-us-.+"}'})]})),children:(0,o.jsx)(c.Icon,{className:d.icon,name:"info-circle",size:"sm"})})]})}),(0,o.jsx)(c.Input,{placeholder:"Search",defaultValue:i,value:u,onChange:e=>{const a=e.target;t(a.value)},"data-testid":"search-query-input",prefix:g,className:d.inputWidth})]})},p=e=>({icon:i.css`
    margin-right: ${e.spacing(.5)};
  `,inputWidth:i.css`
    width: 340px;
    flex-grow: 0;
  `})},"./public/app/features/alerting/unified/components/silences/AmAlertStateTag.tsx":(e,a,t)=>{t.d(a,{G:()=>l});t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js");var s=t("./public/app/plugins/datasource/alertmanager/types.ts"),r=t("./public/app/features/alerting/unified/components/StateTag.tsx"),n=t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");const i={[s.Z9.Active]:"bad",[s.Z9.Unprocessed]:"neutral",[s.Z9.Suppressed]:"info"},l=e=>{let{state:a}=e;return(0,n.jsx)(r.i,{state:i[a],children:a})}},"./public/app/features/alerting/unified/hooks/useAlertManagerSourceName.ts":(e,a,t)=>{t.d(a,{k:()=>c});var s=t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js"),r=t("./public/app/core/hooks/useQueryParams.ts"),n=t("./public/app/core/store.ts"),i=t("./public/app/features/alerting/unified/utils/constants.ts"),l=t("./public/app/features/alerting/unified/utils/datasource.ts");function c(e){const[a,t]=(0,r.K)(),c=function(e){return(0,s.useCallback)((a=>e.map((e=>e.name)).includes(a)),[e])}(e),o=(0,s.useCallback)((e=>{c(e)&&(e===l.GC?(n.Z.delete(i.de),t({[i.c4]:null})):(n.Z.set(i.de,e),t({[i.c4]:e})))}),[t,c]),u=a[i.c4];if(u&&"string"==typeof u)return c(u)?[u,o]:[void 0,o];const p=n.Z.get(i.de);return p&&"string"==typeof p&&c(p)?(o(p),[p,o]):c(l.GC)?[l.GC,o]:[void 0,o]}},"./public/app/features/alerting/unified/hooks/useAlertManagerSources.ts":(e,a,t)=>{t.d(a,{k:()=>n});var s=t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js"),r=t("./public/app/features/alerting/unified/utils/datasource.ts");function n(e){return(0,s.useMemo)((()=>(0,r.LE)(e)),[e])}}}]);
//# sourceMappingURL=AlertGroups.d32aef4f2822e56fb2d6.js.map