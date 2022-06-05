"use strict";(self.webpackChunkgrafana=self.webpackChunkgrafana||[]).push([[5295],{"./public/app/features/manage-dashboards/SnapshotListPage.tsx":(e,a,t)=>{t.r(a),t.d(a,{SnapshotListPage:()=>m,default:()=>y});var s,n,r,c=t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js"),i=t("./.yarn/__virtual__/react-redux-virtual-7ad20a440e/3/opt/drone/yarncache/react-redux-npm-7.2.6-134f5ed64d-0bf142ce0d.zip/node_modules/react-redux/es/index.js"),d=t("./public/app/core/components/Page/Page.tsx"),l=t("./public/app/core/selectors/navModel.ts"),o=t("./.yarn/__virtual__/react-use-virtual-00326e70ba/3/opt/drone/yarncache/react-use-npm-17.3.2-a032cbeb01-7379460f51.zip/node_modules/react-use/lib/useAsync.js"),h=t("./packages/grafana-runtime/src/index.ts"),x=t("./packages/grafana-ui/src/index.ts"),u=t("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");const p=()=>{const[e,a]=(0,c.useState)([]),[t,i]=(0,c.useState)(),d=h.locationService.getLocation().pathname,l=window.location.href,p=l.substring(0,l.indexOf(d));(0,o.Z)((async()=>{const e=await(0,h.getBackendSrv)().get("/api/dashboard/snapshots").then((e=>e.map((e=>Object.assign({},e,{url:`/dashboard/snapshot/${e.key}`})))));a(e)}),[a]);const j=(0,c.useCallback)((async t=>{const s=e.filter((e=>e.key!==t.key));a(s),await(0,h.getBackendSrv)().delete(`/api/snapshots/${t.key}`).catch((()=>{a(e)}))}),[e]);return(0,u.jsxs)("div",{children:[(0,u.jsxs)("table",{className:"filter-table",children:[(0,u.jsx)("thead",{children:(0,u.jsxs)("tr",{children:[s||(s=(0,u.jsx)("th",{children:(0,u.jsx)("strong",{children:"Name"})})),n||(n=(0,u.jsx)("th",{children:(0,u.jsx)("strong",{children:"Snapshot url"})})),(0,u.jsx)("th",{style:{width:"70px"}}),(0,u.jsx)("th",{style:{width:"30px"}}),(0,u.jsx)("th",{style:{width:"25px"}})]})}),(0,u.jsx)("tbody",{children:e.map((e=>{const a=e.externalUrl||e.url,t=e.externalUrl||`${p}${e.url}`;return(0,u.jsxs)("tr",{children:[(0,u.jsx)("td",{children:(0,u.jsx)("a",{href:a,children:e.name})}),(0,u.jsx)("td",{children:(0,u.jsx)("a",{href:a,children:t})}),(0,u.jsx)("td",{children:e.external&&(r||(r=(0,u.jsx)("span",{className:"query-keyword",children:"External"})))}),(0,u.jsx)("td",{className:"text-center",children:(0,u.jsx)(x.LinkButton,{href:a,variant:"secondary",size:"sm",icon:"eye",children:"View"})}),(0,u.jsx)("td",{className:"text-right",children:(0,u.jsx)(x.Button,{variant:"destructive",size:"sm",icon:"times",onClick:()=>i(e)})})]},e.key)}))})]}),(0,u.jsx)(x.ConfirmModal,{isOpen:!!t,icon:"trash-alt",title:"Delete",body:`Are you sure you want to delete '${null==t?void 0:t.name}'?`,confirmText:"Delete",onDismiss:()=>i(void 0),onConfirm:()=>{j(t),i(void 0)}})]})};var j;const m=e=>{let{navModel:a,location:t}=e;return(0,u.jsx)(d.Z,{navModel:a,children:j||(j=(0,u.jsx)(d.Z.Contents,{children:(0,u.jsx)(p,{})}))})},y=(0,i.connect)((e=>({navModel:(0,l.h)(e.navIndex,"snapshots")})))(m)}}]);
//# sourceMappingURL=SnapshotListPage.d32aef4f2822e56fb2d6.js.map