"use strict";(self.webpackChunkgrafana=self.webpackChunkgrafana||[]).push([[4253],{"./public/app/features/datasources/NewDataSourcePage.tsx":(e,a,s)=>{s.r(a),s.d(a,{default:()=>L,getNavModel:()=>N});var r,t=s("./.yarn/__virtual__/@emotion-css-virtual-72c314ddb1/3/opt/drone/yarncache/@emotion-css-npm-11.7.1-25ff8755a7-ac1f56656f.zip/node_modules/@emotion/css/dist/emotion-css.esm.js"),n=s("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js"),i=s("./.yarn/__virtual__/react-redux-virtual-7ad20a440e/3/opt/drone/yarncache/react-redux-npm-7.2.6-134f5ed64d-0bf142ce0d.zip/node_modules/react-redux/es/index.js"),o=s("./packages/grafana-e2e-selectors/src/index.ts"),c=s("./packages/grafana-ui/src/index.ts"),l=s("./public/app/core/components/Page/Page.tsx"),u=s("./packages/grafana-data/src/index.ts"),d=s("./public/app/features/plugins/admin/state/hooks.ts"),p=s("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");function g(){const e=(0,d.UQ)(),{isLoading:a}=(0,d.ZV)(),s=(0,c.useTheme)();return a||0===e.length?null:(0,p.jsx)(c.InfoBox,{"aria-label":o.wl.pages.PluginsList.signatureErrorNotice,severity:"warning",urlTitle:"Read more about plugin signing",url:"https://grafana.com/docs/grafana/latest/plugins/plugin-signatures/",children:(0,p.jsxs)("div",{children:[r||(r=(0,p.jsx)("p",{children:"Unsigned plugins were found during plugin initialization. Grafana Labs cannot guarantee the integrity of these plugins. We recommend only using signed plugins."})),"The following plugins are disabled and not shown in the list below:",(0,p.jsx)(c.List,{items:e,className:t.css`
            list-style-type: circle;
          `,renderItem:e=>(0,p.jsx)("div",{className:t.css`
                margin-top: ${s.spacing.sm};
              `,children:(0,p.jsxs)(c.HorizontalGroup,{spacing:"sm",justify:"flex-start",align:"center",children:[(0,p.jsx)("strong",{children:e.pluginId}),(0,p.jsx)(c.PluginSignatureBadge,{status:m(e.errorCode),className:t.css`
                    margin-top: 0;
                  `})]})})})]})})}function m(e){switch(e){case u.PluginErrorCode.invalidSignature:return u.PluginSignatureStatus.invalid;case u.PluginErrorCode.missingSignature:return u.PluginSignatureStatus.missing;case u.PluginErrorCode.modifiedSignature:return u.PluginSignatureStatus.modified;default:return u.PluginSignatureStatus.missing}}var h,f,x,y,S=s("./public/app/features/datasources/state/actions.ts"),b=s("./public/app/features/datasources/state/reducers.ts"),v=s("./public/app/features/datasources/state/selectors.ts");function P(e,a,s){return a in e?Object.defineProperty(e,a,{value:s,enumerable:!0,configurable:!0,writable:!0}):e[a]=s,e}const j={addDataSource:S.J_,loadDataSourcePlugins:S.Kj,setDataSourceTypeSearchQuery:b.Ht},C=(0,i.connect)((function(e){return{navModel:N(),plugins:(0,v.xo)(e.dataSources),searchQuery:e.dataSources.dataSourceTypeSearchQuery,categories:e.dataSources.categories,isLoading:e.dataSources.isLoadingDataSources}}),j);class _ extends n.PureComponent{constructor(){super(...arguments),P(this,"onDataSourceTypeClicked",(e=>{this.props.addDataSource(e)})),P(this,"onSearchQueryChange",(e=>{this.props.setDataSourceTypeSearchQuery(e)})),P(this,"onLearnMoreClick",(e=>{e.stopPropagation()}))}componentDidMount(){this.props.loadDataSourcePlugins()}renderPlugins(e,a){return e&&e.length?(0,p.jsx)(c.List,{items:e,className:t.css`
          > li {
            margin-bottom: 2px;
          }
        `,getItemKey:e=>e.id.toString(),renderItem:e=>(0,p.jsx)(D,{plugin:e,onClick:()=>this.onDataSourceTypeClicked(e),onLearnMoreClick:this.onLearnMoreClick}),"aria-labelledby":a}):null}renderCategories(){const{categories:e}=this.props;return(0,p.jsxs)(p.Fragment,{children:[e.map((e=>(0,p.jsxs)("div",{className:"add-data-source-category",children:[(0,p.jsx)("div",{className:"add-data-source-category__header",id:e.id,children:e.title}),this.renderPlugins(e.plugins,e.id)]},e.id))),h||(h=(0,p.jsx)("div",{className:"add-data-source-more",children:(0,p.jsx)(c.LinkButton,{variant:"secondary",href:"https://grafana.com/plugins?type=datasource&utm_source=grafana_add_ds",target:"_blank",rel:"noopener",children:"Find more data source plugins on grafana.com"})}))]})}render(){const{navModel:e,isLoading:a,searchQuery:s,plugins:r}=this.props;return(0,p.jsx)(l.Z,{navModel:e,children:(0,p.jsxs)(l.Z.Contents,{isLoading:a,children:[(0,p.jsxs)("div",{className:"page-action-bar",children:[(0,p.jsx)(c.FilterInput,{value:s,onChange:this.onSearchQueryChange,placeholder:"Filter by name or type"}),f||(f=(0,p.jsx)("div",{className:"page-action-bar__spacer"})),x||(x=(0,p.jsx)(c.LinkButton,{href:"datasources",fill:"outline",variant:"secondary",icon:"arrow-left",children:"Cancel"}))]}),!s&&(y||(y=(0,p.jsx)(g,{}))),(0,p.jsxs)("div",{children:[s&&this.renderPlugins(r),!s&&this.renderCategories()]})]})})}}const D=e=>{var a,s;const{plugin:r,onLearnMoreClick:n}=e,i="phantom"===r.module,l=i||r.unlicensed?()=>{}:e.onClick,u=(null===(a=r.info)||void 0===a||null===(s=a.links)||void 0===s?void 0:s.length)>0?r.info.links[0]:null,d=(0,c.useStyles2)(k);return(0,p.jsxs)(c.Card,{className:(0,t.cx)(d.card,"card-parent"),onClick:l,children:[(0,p.jsx)(c.Card.Heading,{className:d.heading,"aria-label":o.wl.pages.AddDataSource.dataSourcePluginsV2(r.name),children:r.name}),(0,p.jsx)(c.Card.Figure,{align:"center",className:d.figure,children:(0,p.jsx)("img",{className:d.logo,src:r.info.logos.small,alt:""})}),(0,p.jsx)(c.Card.Description,{className:d.description,children:r.info.description}),!i&&(0,p.jsx)(c.Card.Meta,{className:d.meta,children:(0,p.jsx)(c.PluginSignatureBadge,{status:r.signature})}),(0,p.jsx)(c.Card.Actions,{className:d.actions,children:u&&(0,p.jsx)(c.LinkButton,{variant:"secondary",href:`${u.url}?utm_source=grafana_add_ds`,target:"_blank",rel:"noopener",onClick:n,icon:"external-link-alt","aria-label":`${r.name}, learn more.`,children:u.name})})]})};function k(e){return{heading:(0,t.css)({fontSize:e.v1.typography.heading.h5,fontWeight:"inherit"}),figure:(0,t.css)({width:"inherit",marginRight:"0px","> img":{width:e.spacing(7)}}),meta:(0,t.css)({marginTop:"6px",position:"relative"}),description:(0,t.css)({margin:"0px",fontSize:e.typography.size.sm}),actions:(0,t.css)({position:"relative",alignSelf:"center",marginTop:"0px",opacity:0,".card-parent:hover &, .card-parent:focus-within &":{opacity:1}}),card:(0,t.css)({gridTemplateAreas:'\n      "Figure   Heading   Actions"\n      "Figure Description Actions"\n      "Figure    Meta     Actions"\n      "Figure     -       Actions"'}),logo:(0,t.css)({marginRight:e.v1.spacing.lg,marginLeft:e.v1.spacing.sm,width:e.spacing(7),maxHeight:e.spacing(7)})}}function N(){const e={icon:"database",id:"datasource-new",text:"Add data source",href:"datasources/new",subTitle:"Choose a data source type"};return{main:e,node:e}}const L=C(_)},"./public/app/features/plugins/admin/state/hooks.ts":(e,a,s)=>{s.d(a,{iY:()=>M,bt:()=>N,ZV:()=>k,GE:()=>v,UQ:()=>j,bJ:()=>P,x3:()=>C,IS:()=>L,y9:()=>D,S1:()=>_,wq:()=>w});var r=s("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js"),t=s("./.yarn/__virtual__/react-redux-virtual-7ad20a440e/3/opt/drone/yarncache/react-redux-npm-7.2.6-134f5ed64d-0bf142ce0d.zip/node_modules/react-redux/es/index.js"),n=s("./public/app/features/plugins/admin/helpers.ts"),i=s("./public/app/features/plugins/admin/state/actions.ts"),o=s("./public/app/features/plugins/admin/state/reducer.ts"),c=s("../../opt/drone/yarncache/reselect-npm-4.1.5-bc046e41ae-54c13c1e79.zip/node_modules/reselect/es/index.js"),l=s("./public/app/features/plugins/admin/types.ts");const u=e=>e.plugins,d=(0,c.P1)(u,(e=>{let{items:a}=e;return a})),p=(0,c.P1)(u,(e=>{let{settings:a}=e;return a.displayMode})),{selectAll:g,selectById:m}=o.CD.getSelectors(d),h=(e,a)=>(0,c.P1)((e=>(0,c.P1)(g,(a=>a.filter((a=>"installed"===e?a.isInstalled:!a.isCore)))))(e),(e=>e.filter((e=>"all"===a||e.type===a)))),f=(e,a,s)=>(0,c.P1)(h(a,s),(e=>(0,c.P1)(g,(a=>""===e?[]:a.filter((a=>{const s=[];return a.name&&s.push(a.name.toLowerCase()),a.orgName&&s.push(a.orgName.toLowerCase()),s.some((a=>a.includes(e.toLowerCase())))})))))(e),((a,s)=>""===e?a:s)),x=(0,c.P1)(g,(e=>e?e.filter((e=>Boolean(e.error))).map((e=>({pluginId:e.id,errorCode:e.error}))):[])),y=e=>(0,c.P1)(u,(a=>{let{requests:s={}}=a;return s[e]})),S=e=>(0,c.P1)(y(e),(e=>(null==e?void 0:e.status)===l.eE.Pending)),b=e=>(0,c.P1)(y(e),(e=>(null==e?void 0:e.status)===l.eE.Rejected?null==e?void 0:e.error:null)),v=e=>{let{query:a="",filterBy:s="installed",filterByType:r="all",sortBy:i=n.Nh.nameAsc}=e;T();const o=(0,t.useSelector)(f(a,s,r)),{isLoading:c,error:l}=k();return{isLoading:c,error:l,plugins:(0,n.AA)(o,i)}},P=e=>(T(),z(e),(0,t.useSelector)((a=>m(a,e)))),j=()=>(T(),(0,t.useSelector)(x)),C=()=>{const e=(0,t.useDispatch)();return(a,s,r)=>e((0,i.N9)({id:a,version:s,isUpdating:r}))},_=()=>{const e=(0,t.useDispatch)();return a=>e((0,i.Tz)(a))},D=()=>null===(0,t.useSelector)(b(i.tQ.typePrefix)),k=()=>({isLoading:(0,t.useSelector)(S(i.Qd.typePrefix)),error:(0,t.useSelector)(b(i.Qd.typePrefix))}),N=()=>({isLoading:(0,t.useSelector)(S(i.DD.typePrefix)),error:(0,t.useSelector)(b(i.DD.typePrefix))}),L=()=>({isInstalling:(0,t.useSelector)(S(i.N9.typePrefix)),error:(0,t.useSelector)(b(i.N9.typePrefix))}),w=()=>({isUninstalling:(0,t.useSelector)(S(i.Tz.typePrefix)),error:(0,t.useSelector)(b(i.Tz.typePrefix))}),T=()=>{const e=(0,t.useDispatch)(),a=(0,t.useSelector)((s=i.Qd.typePrefix,(0,c.P1)(y(s),(e=>void 0===e))));var s;(0,r.useEffect)((()=>{a&&e((0,i.Qd)())}),[])},z=e=>{const a=(0,t.useDispatch)(),s=(0,t.useSelector)((a=>m(a,e))),n=!(0,t.useSelector)(S(i.DD.typePrefix))&&s&&!s.details;(0,r.useEffect)((()=>{n&&a((0,i.DD)(e))}),[s])},M=()=>{const e=(0,t.useDispatch)();return{displayMode:(0,t.useSelector)(p),setDisplayMode:a=>e((0,o.UC)(a))}}}}]);
//# sourceMappingURL=NewDataSourcePage.d32aef4f2822e56fb2d6.js.map