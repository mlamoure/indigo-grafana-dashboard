"use strict";(self.webpackChunkgrafana=self.webpackChunkgrafana||[]).push([[3203],{"./public/app/features/query/components/QueryGroup.tsx":(e,t,s)=>{s.d(t,{D:()=>H});var i,n,a=s("./.yarn/__virtual__/@emotion-css-virtual-72c314ddb1/3/opt/drone/yarncache/@emotion-css-npm-11.7.1-25ff8755a7-ac1f56656f.zip/node_modules/@emotion/css/dist/emotion-css.esm.js"),r=s("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js"),o=s("./packages/grafana-data/src/index.ts"),l=s("./packages/grafana-e2e-selectors/src/index.ts"),d=s("./packages/grafana-runtime/src/index.ts"),c=s("./packages/grafana-ui/src/index.ts"),u=s("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");function h(e,t,s){return t in e?Object.defineProperty(e,t,{value:s,enumerable:!0,configurable:!0,writable:!0}):e[t]=s,e}class p extends r.PureComponent{constructor(){super(...arguments),h(this,"state",{isError:!1,isLoading:!1,help:""}),h(this,"loadHelp",(()=>{const{plugin:e,type:t}=this.props;this.setState({isLoading:!0}),(0,d.getBackendSrv)().get(`/api/plugins/${e.id}/markdown/${t}`).then((e=>{const s=(0,o.renderMarkdown)(e);""===e&&"help"===t?this.setState({isError:!1,isLoading:!1,help:this.constructPlaceholderInfo()}):this.setState({isError:!1,isLoading:!1,help:s})})).catch((()=>{this.setState({isError:!0,isLoading:!1})}))}))}componentDidMount(){this.loadHelp()}constructPlaceholderInfo(){return"No plugin help or readme markdown file was found"}render(){const{type:e}=this.props,{isError:t,isLoading:s,help:a}=this.state;return s?i||(i=(0,u.jsx)("h2",{children:"Loading help..."})):t?n||(n=(0,u.jsx)("h3",{children:"'Error occurred when loading help'"})):(0,u.jsx)("div",{className:"markdown-html",dangerouslySetInnerHTML:{__html:a}})}}var m=s("./public/app/core/config.ts"),g=s("./public/app/core/services/backend_srv.ts"),x=s("./public/app/core/utils/query.ts"),v=s("./public/app/features/expressions/ExpressionDatasource.ts"),f=s("./public/app/plugins/datasource/dashboard/index.ts"),S=s("./packages/grafana-runtime/src/utils/DataSourceWithBackend.ts");var y,j,b,C,w,O,R,I,Q,T=s("./public/app/features/query/components/QueryActionComponent.ts"),D=s("./public/app/features/query/components/QueryEditorRows.tsx"),q=s("./public/app/core/components/QueryOperationRow/QueryOperationRow.tsx");function k(e,t,s){return t in e?Object.defineProperty(e,t,{value:s,enumerable:!0,configurable:!0,writable:!0}):e[t]=s,e}class N extends r.PureComponent{constructor(e){var t,s,i,n;super(e),k(this,"onRelativeTimeChange",(e=>{this.setState({timeRangeFrom:e.target.value})})),k(this,"onTimeShiftChange",(e=>{this.setState({timeRangeShift:e.target.value})})),k(this,"onOverrideTime",(e=>{var t;const{options:s,onChange:i}=this.props,n=P(e.target.value),a=A(n);var r;a&&(null===(t=s.timeRange)||void 0===t?void 0:t.from)!==n&&i(Object.assign({},s,{timeRange:Object.assign({},null!==(r=s.timeRange)&&void 0!==r?r:{},{from:n})}));this.setState({relativeTimeIsValid:a})})),k(this,"onTimeShift",(e=>{var t;const{options:s,onChange:i}=this.props,n=P(e.target.value),a=A(n);var r;a&&(null===(t=s.timeRange)||void 0===t?void 0:t.shift)!==n&&i(Object.assign({},s,{timeRange:Object.assign({},null!==(r=s.timeRange)&&void 0!==r?r:{},{shift:n})}));this.setState({timeShiftIsValid:a})})),k(this,"onToggleTimeOverride",(()=>{const{onChange:e,options:t}=this.props;this.setState({timeRangeHide:!this.state.timeRangeHide},(()=>{var s;e(Object.assign({},t,{timeRange:Object.assign({},null!==(s=t.timeRange)&&void 0!==s?s:{},{hide:this.state.timeRangeHide})}))}))})),k(this,"onCacheTimeoutBlur",(e=>{const{options:t,onChange:s}=this.props;s(Object.assign({},t,{cacheTimeout:P(e.target.value)}))})),k(this,"onMaxDataPointsBlur",(e=>{const{options:t,onChange:s}=this.props;let i=parseInt(e.target.value,10);(isNaN(i)||0===i)&&(i=null),i!==t.maxDataPoints&&s(Object.assign({},t,{maxDataPoints:i}))})),k(this,"onMinIntervalBlur",(e=>{const{options:t,onChange:s}=this.props,i=P(e.target.value);i!==t.minInterval&&s(Object.assign({},t,{minInterval:i}))})),k(this,"onOpenOptions",(()=>{this.setState({isOpen:!0})})),k(this,"onCloseOptions",(()=>{this.setState({isOpen:!1})}));const{options:a}=e;this.state={timeRangeFrom:(null===(t=a.timeRange)||void 0===t?void 0:t.from)||"",timeRangeShift:(null===(s=a.timeRange)||void 0===s?void 0:s.shift)||"",timeRangeHide:null!==(i=null===(n=a.timeRange)||void 0===n?void 0:n.hide)&&void 0!==i&&i,isOpen:!1,relativeTimeIsValid:!0,timeShiftIsValid:!0}}renderCacheTimeoutOption(){var e,t;const{dataSource:s,options:i}=this.props;return null!==(e=s.meta.queryOptions)&&void 0!==e&&e.cacheTimeout?(0,u.jsx)("div",{className:"gf-form-inline",children:(0,u.jsxs)("div",{className:"gf-form",children:[(0,u.jsx)(c.InlineFormLabel,{width:9,tooltip:"If your time series store has a query cache this option can override the default cache timeout. Specify a\n    numeric value in seconds.",children:"Cache timeout"}),(0,u.jsx)(c.Input,{type:"text",className:"width-6",placeholder:"60",spellCheck:!1,onBlur:this.onCacheTimeoutBlur,defaultValue:null!==(t=i.cacheTimeout)&&void 0!==t?t:""})]})}):null}renderMaxDataPointsOption(){var e,t;const{data:s,options:i}=this.props,n=null===(e=s.request)||void 0===e?void 0:e.maxDataPoints,a=null!==(t=i.maxDataPoints)&&void 0!==t?t:"",r=""===a;return(0,u.jsx)("div",{className:"gf-form-inline",children:(0,u.jsxs)("div",{className:"gf-form",children:[y||(y=(0,u.jsx)(c.InlineFormLabel,{width:9,tooltip:(0,u.jsx)(u.Fragment,{children:"The maximum data points per series. Used directly by some data sources and used in calculation of auto interval. With streaming data this value is used for the rolling buffer."}),children:"Max data points"})),(0,u.jsx)(c.Input,{type:"number",className:"width-6",placeholder:`${n}`,spellCheck:!1,onBlur:this.onMaxDataPointsBlur,defaultValue:a}),r&&(0,u.jsxs)(u.Fragment,{children:[j||(j=(0,u.jsx)("div",{className:"gf-form-label query-segment-operator",children:"="})),b||(b=(0,u.jsx)("div",{className:"gf-form-label",children:"Width of panel"}))]})]})})}renderIntervalOption(){var e,t,s;const{data:i,dataSource:n,options:a}=this.props,r=null===(e=i.request)||void 0===e?void 0:e.interval,o=null!==(t=n.interval)&&void 0!==t?t:"No limit";return(0,u.jsxs)(u.Fragment,{children:[(0,u.jsx)("div",{className:"gf-form-inline",children:(0,u.jsxs)("div",{className:"gf-form",children:[C||(C=(0,u.jsx)(c.InlineFormLabel,{width:9,tooltip:(0,u.jsxs)(u.Fragment,{children:["A lower limit for the interval. Recommended to be set to write frequency, for example ",(0,u.jsx)("code",{children:"1m"})," ","if your data is written every minute. Default value can be set in data source settings for most data sources."]}),children:"Min interval"})),(0,u.jsx)(c.Input,{type:"text",className:"width-6",placeholder:`${o}`,spellCheck:!1,onBlur:this.onMinIntervalBlur,defaultValue:null!==(s=a.minInterval)&&void 0!==s?s:""})]})}),(0,u.jsx)("div",{className:"gf-form-inline",children:(0,u.jsxs)("div",{className:"gf-form",children:[w||(w=(0,u.jsx)(c.InlineFormLabel,{width:9,tooltip:(0,u.jsxs)(u.Fragment,{children:["The evaluated interval that is sent to data source and is used in ",(0,u.jsx)("code",{children:"$__interval"})," and"," ",(0,u.jsx)("code",{children:"$__interval_ms"})]}),children:"Interval"})),(0,u.jsx)(c.InlineFormLabel,{width:6,children:r}),O||(O=(0,u.jsx)("div",{className:"gf-form-label query-segment-operator",children:"="})),R||(R=(0,u.jsx)("div",{className:"gf-form-label",children:"Time range / max data points"}))]})})]})}renderCollapsedText(e){var t;const{data:s,options:i}=this.props,{isOpen:n}=this.state;if(n)return;let a=null!==(t=i.maxDataPoints)&&void 0!==t?t:"";""===a&&s.request&&(a=`auto = ${s.request.maxDataPoints}`);let r=i.minInterval;return s.request&&(r=`${s.request.interval}`),(0,u.jsxs)(u.Fragment,{children:[(0,u.jsxs)("div",{className:e.collapsedText,children:["MD = ",a]}),(0,u.jsxs)("div",{className:e.collapsedText,children:["Interval = ",r]})]})}render(){const{timeRangeHide:e,relativeTimeIsValid:t,timeShiftIsValid:s}=this.state,{timeRangeFrom:i,timeRangeShift:n,isOpen:a}=this.state,r=B();return(0,u.jsxs)(q.t,{id:"Query options",index:0,title:"Query options",headerElement:this.renderCollapsedText(r),isOpen:a,onOpen:this.onOpenOptions,onClose:this.onCloseOptions,children:[this.renderMaxDataPointsOption(),this.renderIntervalOption(),this.renderCacheTimeoutOption(),(0,u.jsxs)("div",{className:"gf-form",children:[I||(I=(0,u.jsx)(c.InlineFormLabel,{width:9,children:"Relative time"})),(0,u.jsx)(c.Input,{type:"text",className:"width-6",placeholder:"1h",onChange:this.onRelativeTimeChange,onBlur:this.onOverrideTime,invalid:!t,value:i})]}),(0,u.jsxs)("div",{className:"gf-form",children:[Q||(Q=(0,u.jsx)("span",{className:"gf-form-label width-9",children:"Time shift"})),(0,u.jsx)(c.Input,{type:"text",className:"width-6",placeholder:"1h",onChange:this.onTimeShiftChange,onBlur:this.onTimeShift,invalid:!s,value:n})]}),(n||i)&&(0,u.jsx)("div",{className:"gf-form-inline",children:(0,u.jsx)(c.InlineField,{label:"Hide time info",labelWidth:18,children:(0,u.jsx)(c.Switch,{value:e,onChange:this.onToggleTimeOverride})})})]})}}const A=e=>!e||o.rangeUtil.isValidTimeSpan(e),P=e=>""===e?null:e,B=(0,c.stylesFactory)((()=>{const{theme:e}=m.vc;return{collapsedText:a.css`
      margin-left: ${e.spacing.md};
      font-size: ${e.typography.size.sm};
      color: ${e.colors.textWeak};
    `}}));var F,M;function E(e,t,s){return t in e?Object.defineProperty(e,t,{value:s,enumerable:!0,configurable:!0,writable:!0}):e[t]=s,e}class H extends r.PureComponent{constructor(){super(...arguments),E(this,"backendSrv",g.ae),E(this,"dataSourceSrv",(0,d.getDataSourceSrv)()),E(this,"querySubscription",null),E(this,"state",{isLoadingHelp:!1,helpContent:null,isPickerOpen:!1,isAddingMixed:!1,isHelpOpen:!1,queries:[],data:{state:o.LoadingState.NotStarted,series:[],timeRange:(0,o.getDefaultTimeRange)()}}),E(this,"onChangeDataSource",(async e=>{const{dsSettings:t}=this.state,s=t?await(0,d.getDataSourceSrv)().get(t.uid):void 0,i=await(0,d.getDataSourceSrv)().get(e.uid),n=await async function(e,t,s,i){let n=s;const a={type:e.type,uid:t};if((null==i?void 0:i.meta.id)!==e.meta.id){if(e.meta.mixed)return s;if((0,o.hasQueryExportSupport)(i)&&(0,o.hasQueryImportSupport)(e)){const t=await i.exportToAbstractQueries(s);n=await e.importFromAbstractQueries(t)}else{if(!i||!e.importQueries)return[{refId:"A",datasource:a}];n=await e.importQueries(s,i)}}return 0===n.length?[{refId:"A",datasource:a}]:n.map((t=>((0,S.Pr)(t.datasource)||e.meta.mixed||(t.datasource=a),t)))}(i,e.uid,this.state.queries,s),a=await this.dataSourceSrv.get(e.name);this.onChange({queries:n,dataSource:{name:e.name,uid:e.uid,type:e.meta.id,default:e.isDefault}}),this.setState({queries:n,dataSource:a,dsSettings:e})})),E(this,"onAddQueryClick",(()=>{const{queries:e}=this.state;this.onQueriesChange((0,x.DI)(e,this.newQuery())),this.onScrollBottom()})),E(this,"onAddExpressionClick",(()=>{this.onQueriesChange((0,x.DI)(this.state.queries,v.mV.newQuery())),this.onScrollBottom()})),E(this,"onScrollBottom",(()=>{setTimeout((()=>{this.state.scrollElement&&this.state.scrollElement.scrollTo({top:1e4})}),20)})),E(this,"onUpdateAndRun",(e=>{this.props.onOptionsChange(e),this.props.onRunQueries()})),E(this,"onOpenHelp",(()=>{this.setState({isHelpOpen:!0})})),E(this,"onCloseHelp",(()=>{this.setState({isHelpOpen:!1})})),E(this,"renderMixedPicker",(()=>(0,u.jsx)(d.DataSourcePicker,{mixed:!1,onChange:this.onAddMixedQuery,current:null,autoFocus:!0,variables:!0,onBlur:this.onMixedPickerBlur,openMenuOnFocus:!0}))),E(this,"onAddMixedQuery",(e=>{this.onAddQuery({datasource:e.name}),this.setState({isAddingMixed:!1})})),E(this,"onMixedPickerBlur",(()=>{this.setState({isAddingMixed:!1})})),E(this,"onAddQuery",(e=>{const{dsSettings:t,queries:s}=this.state;this.onQueriesChange((0,x.DI)(s,e,{type:null==t?void 0:t.type,uid:null==t?void 0:t.uid})),this.onScrollBottom()})),E(this,"onQueriesChange",(e=>{this.onChange({queries:e}),this.setState({queries:e})})),E(this,"setScrollRef",(e=>{this.setState({scrollElement:e})}))}async componentDidMount(){const{queryRunner:e,options:t}=this.props;this.querySubscription=e.getData({withTransforms:!1,withFieldConfig:!1}).subscribe({next:e=>this.onPanelDataUpdate(e)});try{const e=await this.dataSourceSrv.get(t.dataSource),s=this.dataSourceSrv.getInstanceSettings(t.dataSource),i=await this.dataSourceSrv.get(),n=e.getRef(),a=t.queries.map((e=>e.datasource?e:Object.assign({},e,{datasource:n})));this.setState({queries:a,dataSource:e,dsSettings:s,defaultDataSource:i})}catch(e){console.log("failed to load data source",e)}}componentWillUnmount(){this.querySubscription&&(this.querySubscription.unsubscribe(),this.querySubscription=null)}onPanelDataUpdate(e){this.setState({data:e})}newQuery(){const{dsSettings:e,defaultDataSource:t}=this.state,s=null!=e&&e.meta.mixed?t:e;return{datasource:{uid:null==s?void 0:s.uid,type:null==s?void 0:s.type}}}onChange(e){this.props.onOptionsChange(Object.assign({},this.props.options,e))}renderTopSection(e){const{onOpenQueryInspector:t,options:s}=this.props,{dataSource:i,data:n}=this.state;return(0,u.jsx)("div",{children:(0,u.jsxs)("div",{className:e.dataSourceRow,children:[F||(F=(0,u.jsx)(c.InlineFormLabel,{htmlFor:"data-source-picker",width:"auto",children:"Data source"})),(0,u.jsx)("div",{className:e.dataSourceRowItem,children:(0,u.jsx)(d.DataSourcePicker,{onChange:this.onChangeDataSource,current:s.dataSource,metrics:!0,mixed:!0,dashboard:!0,variables:!0})}),i&&(0,u.jsxs)(u.Fragment,{children:[(0,u.jsx)("div",{className:e.dataSourceRowItem,children:(0,u.jsx)(c.Button,{variant:"secondary",icon:"question-circle",title:"Open data source help",onClick:this.onOpenHelp})}),(0,u.jsx)("div",{className:e.dataSourceRowItemOptions,children:(0,u.jsx)(N,{options:s,dataSource:i,data:n,onChange:this.onUpdateAndRun})}),t&&(0,u.jsx)("div",{className:e.dataSourceRowItem,children:(0,u.jsx)(c.Button,{variant:"secondary",onClick:t,"aria-label":l.wl.components.QueryTab.queryInspectorButton,children:"Query inspector"})})]})]})})}renderQueries(e){const{onRunQueries:t}=this.props,{data:s,queries:i}=this.state;return(0,f.yl)(e.name)?(0,u.jsx)(f.hD,{queries:i,panelData:s,onChange:this.onQueriesChange,onRunQueries:t}):(0,u.jsx)("div",{"aria-label":l.wl.components.QueryTab.content,children:(0,u.jsx)(D.l,{queries:i,dsSettings:e,onQueriesChange:this.onQueriesChange,onAddQuery:this.onAddQuery,onRunQueries:t,data:s})})}isExpressionsSupported(e){return!0===(e.meta.alerting||e.meta.mixed)}renderExtraActions(){return T.S.getAllExtraRenderAction().map(((e,t)=>e({onAddQuery:this.onAddQuery,onChangeDataSource:this.onChangeDataSource,key:t}))).filter(Boolean)}renderAddQueryRow(e,t){const{isAddingMixed:s}=this.state,i=!(s||(0,f.yl)(e.name));return(0,u.jsxs)(c.HorizontalGroup,{spacing:"md",align:"flex-start",children:[i&&(0,u.jsx)(c.Button,{icon:"plus",onClick:this.onAddQueryClick,variant:"secondary","aria-label":l.wl.components.QueryTab.addQuery,children:"Query"}),m.ZP.expressionsEnabled&&this.isExpressionsSupported(e)&&(0,u.jsx)(c.Button,{icon:"plus",onClick:this.onAddExpressionClick,variant:"secondary",className:t.expressionButton,children:M||(M=(0,u.jsx)("span",{children:"Expression "}))}),this.renderExtraActions()]})}render(){const{isHelpOpen:e,dsSettings:t}=this.state,s=L();return(0,u.jsx)(c.CustomScrollbar,{autoHeightMin:"100%",scrollRefCallback:this.setScrollRef,children:(0,u.jsxs)("div",{className:s.innerWrapper,children:[this.renderTopSection(s),t&&(0,u.jsxs)(u.Fragment,{children:[(0,u.jsx)("div",{className:s.queriesWrapper,children:this.renderQueries(t)}),this.renderAddQueryRow(t,s),e&&(0,u.jsx)(c.Modal,{title:"Data source help",isOpen:!0,onDismiss:this.onCloseHelp,children:(0,u.jsx)(p,{plugin:t.meta,type:"query_help"})})]})]})})}}const L=(0,c.stylesFactory)((()=>{const{theme:e}=m.ZP;return{innerWrapper:a.css`
      display: flex;
      flex-direction: column;
      padding: ${e.spacing.md};
    `,dataSourceRow:a.css`
      display: flex;
      margin-bottom: ${e.spacing.md};
    `,dataSourceRowItem:a.css`
      margin-right: ${e.spacing.inlineFormMargin};
    `,dataSourceRowItemOptions:a.css`
      flex-grow: 1;
      margin-right: ${e.spacing.inlineFormMargin};
    `,queriesWrapper:a.css`
      padding-bottom: 16px;
    `,expressionWrapper:a.css``,expressionButton:a.css`
      margin-right: ${e.spacing.sm};
    `}}))}}]);
//# sourceMappingURL=3203.d32aef4f2822e56fb2d6.js.map