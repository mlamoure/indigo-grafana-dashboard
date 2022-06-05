"use strict";(self.webpackChunkgrafana=self.webpackChunkgrafana||[]).push([[534],{"./public/app/plugins/datasource/postgres/module.ts":(e,t,a)=>{a.r(t),a.d(t,{plugin:()=>M});var r=a("./packages/grafana-data/src/index.ts"),s=a("../../opt/drone/yarncache/lodash-npm-4.17.21-6382451519-eb835a2e51.zip/node_modules/lodash/lodash.js"),i=a("./public/app/features/datasources/utils/passwordHandlers.ts");function n(e,t,a){return t in e?Object.defineProperty(e,t,{value:a,enumerable:!0,configurable:!0,writable:!0}):e[t]=a,e}class l{constructor(e,t){n(this,"datasourceSrv",void 0),n(this,"showTimescaleDBHelp",void 0),n(this,"onPasswordReset",void 0),n(this,"onPasswordChange",void 0),n(this,"postgresVersions",[{name:"9.3",value:903},{name:"9.4",value:904},{name:"9.5",value:905},{name:"9.6",value:906},{name:"10",value:1e3},{name:"11",value:1100},{name:"12+",value:1200}]),this.current=e.ctrl.current,this.datasourceSrv=t,this.current.jsonData.sslmode=this.current.jsonData.sslmode||"verify-full",this.current.jsonData.tlsConfigurationMethod=this.current.jsonData.tlsConfigurationMethod||"file-path",this.current.jsonData.postgresVersion=this.current.jsonData.postgresVersion||903,this.showTimescaleDBHelp=!1,this.autoDetectFeatures(),this.onPasswordReset=(0,i.Xr)(this,i.HX.Password),this.onPasswordChange=(0,i.wP)(this,i.HX.Password),this.tlsModeMapping()}autoDetectFeatures(){this.current.id&&this.datasourceSrv.loadDatasource(this.current.name).then((e=>e.getVersion().then((t=>{(t=Number(t[0].text))>=906&&e.getTimescaleDBVersion().then((e=>{1===e.length&&(this.current.jsonData.timescaledb=!0)}));const a=Math.trunc(t/100),r=t%100;let i=String(a);t<1e3&&(i=String(a)+"."+String(r)),(0,s.find)(this.postgresVersions,(e=>e.value===t))||this.postgresVersions.push({name:i,value:t}),this.current.jsonData.postgresVersion=t}))))}toggleTimescaleDBHelp(){this.showTimescaleDBHelp=!this.showTimescaleDBHelp}tlsModeMapping(){"disable"===this.current.jsonData.sslmode?(this.current.jsonData.tlsAuth=!1,this.current.jsonData.tlsAuthWithCACert=!1,this.current.jsonData.tlsSkipVerify=!0):(this.current.jsonData.tlsAuth=!0,this.current.jsonData.tlsAuthWithCACert=!0,this.current.jsonData.tlsSkipVerify=!1)}}l.$inject=["$scope","datasourceSrv"],n(l,"templateUrl","partials/config.html");var o=a("../../opt/drone/yarncache/rxjs-npm-7.5.5-d0546b1ccb-e034f60805.zip/node_modules/rxjs/dist/esm5/internal/lastValueFrom.js"),u=a("../../opt/drone/yarncache/rxjs-npm-7.5.5-d0546b1ccb-e034f60805.zip/node_modules/rxjs/dist/esm5/internal/observable/of.js"),m=a("../../opt/drone/yarncache/rxjs-npm-7.5.5-d0546b1ccb-e034f60805.zip/node_modules/rxjs/dist/esm5/internal/operators/map.js"),h=a("../../opt/drone/yarncache/rxjs-npm-7.5.5-d0546b1ccb-e034f60805.zip/node_modules/rxjs/dist/esm5/internal/operators/catchError.js"),c=a("./packages/grafana-runtime/src/index.ts"),p=a("./packages/grafana-runtime/src/utils/queryResponse.ts"),d=a("./public/app/features/templating/template_srv.ts");function g(e,t,a){return t in e?Object.defineProperty(e,t,{value:a,enumerable:!0,configurable:!0,writable:!0}):e[t]=a,e}class y{constructor(e,t,a){g(this,"target",void 0),g(this,"templateSrv",void 0),g(this,"scopedVars",void 0),this.target=e,this.templateSrv=t,this.scopedVars=a,e.format=e.format||"time_series",e.timeColumn=e.timeColumn||"time",e.metricColumn=e.metricColumn||"none",e.group=e.group||[],e.where=e.where||[{type:"macro",name:"$__timeFilter",params:[]}],e.select=e.select||[[{type:"column",params:["value"]}]],"rawQuery"in this.target||(e.rawQuery="rawSql"in e),this.interpolateQueryStr=this.interpolateQueryStr.bind(this)}unquoteIdentifier(e){return'"'===e[0]&&'"'===e[e.length-1]?e.substring(1,e.length-1).replace(/""/g,'"'):e}quoteIdentifier(e){return'"'+String(e).replace(/"/g,'""')+'"'}quoteLiteral(e){return"'"+String(e).replace(/'/g,"''")+"'"}escapeLiteral(e){return String(e).replace(/'/g,"''")}hasTimeGroup(){return(0,s.find)(this.target.group,(e=>"time"===e.type))}hasMetricColumn(){return"none"!==this.target.metricColumn}interpolateQueryStr(e,t,a){if(!t.multi&&!t.includeAll)return this.escapeLiteral(e);if("string"==typeof e)return this.quoteLiteral(e);return(0,s.map)(e,this.quoteLiteral).join(",")}render(e){const t=this.target;return this.target.rawQuery||"table"in this.target?(t.rawQuery||(t.rawSql=this.buildQuery()),e?this.templateSrv.replace(t.rawSql,this.scopedVars,this.interpolateQueryStr):t.rawSql):""}hasUnixEpochTimecolumn(){return["int4","int8","float4","float8","numeric"].indexOf(this.target.timeColumnType)>-1}buildTimeColumn(){let e=!(arguments.length>0&&void 0!==arguments[0])||arguments[0];const t=this.hasTimeGroup();let a,r="$__timeGroup";if(t){let s;s=t.params.length>1&&"none"!==t.params[1]?t.params.join(","):t.params[0],this.hasUnixEpochTimecolumn()&&(r="$__unixEpochGroup"),e&&(r+="Alias"),a=r+"("+this.target.timeColumn+","+s+")"}else a=this.target.timeColumn,e&&(a+=' AS "time"');return a}buildMetricColumn(){return this.hasMetricColumn()?this.target.metricColumn+" AS metric":""}buildValueColumns(){let e="";for(const t of this.target.select)e+=",\n  "+this.buildValueColumn(t);return e}buildValueColumn(e){let t="";t=(0,s.find)(e,(e=>"column"===e.type)).params[0];const a=(0,s.find)(e,(e=>"aggregate"===e.type||"percentile"===e.type)),r=(0,s.find)(e,(e=>"window"===e.type||"moving_window"===e.type));if(a){const e=a.params[0];switch(a.type){case"aggregate":t="first"===e||"last"===e?e+"("+t+","+this.target.timeColumn+")":e+"("+t+")";break;case"percentile":t=e+"("+a.params[1]+") WITHIN GROUP (ORDER BY "+t+")"}}if(r){const e=[];this.hasMetricColumn()&&e.push("PARTITION BY "+this.target.metricColumn),e.push("ORDER BY "+this.buildTimeColumn(!1));const s=e.join(" ");let i,n;switch(r.type){case"window":switch(r.params[0]){case"delta":i=t,n="lag("+i+") OVER ("+s+")",t=i+" - "+n;break;case"increase":i=t,n="lag("+i+") OVER ("+s+")",t="(CASE WHEN "+i+" >= "+n+" THEN "+i+" - "+n,t+=" WHEN "+n+" IS NULL THEN NULL ELSE "+i+" END)";break;case"rate":let e=this.target.timeColumn;a&&(e="min("+e+")"),i=t,n="lag("+i+") OVER ("+s+")",t="(CASE WHEN "+i+" >= "+n+" THEN "+i+" - "+n,t+=" WHEN "+n+" IS NULL THEN NULL ELSE "+i+" END)",t+="/extract(epoch from "+e+" - lag("+e+") OVER ("+s+"))";break;default:t=r.params[0]+"("+t+") OVER ("+s+")"}break;case"moving_window":t=r.params[0]+"("+t+") OVER ("+s+" ROWS "+r.params[1]+" PRECEDING)"}}const i=(0,s.find)(e,(e=>"alias"===e.type));return i&&(t+=" AS "+this.quoteIdentifier(i.params[0])),t}buildWhereClause(){let e="";const t=(0,s.map)(this.target.where,((e,t)=>{switch(e.type){case"macro":return e.name+"("+this.target.timeColumn+")";case"expression":return e.params.join(" ")}}));return t.length>0&&(e="\nWHERE\n  "+t.join(" AND\n  ")),e}buildGroupClause(){let e="",t="";for(let e=0;e<this.target.group.length;e++){const a=this.target.group[e];e>0&&(t+=", "),"time"===a.type?t+="1":t+=a.params[0]}return t.length&&(e="\nGROUP BY "+t,this.hasMetricColumn()&&(e+=",2")),e}buildQuery(){let e="SELECT";return e+="\n  "+this.buildTimeColumn(),this.hasMetricColumn()&&(e+=",\n  "+this.buildMetricColumn()),e+=this.buildValueColumns(),e+="\nFROM "+this.target.table,e+=this.buildWhereClause(),e+=this.buildGroupClause(),e+="\nORDER BY 1",this.hasMetricColumn()&&(e+=",2"),e}}y.$inject=["target","templateSrv","scopedVars"];var f=a("./public/app/features/variables/utils.ts");class v{transformMetricFindResponse(e){const t=(0,c.toDataQueryResponse)(e).data;if(!t||!t.length)return[];const a=t[0],r=[],s=a.fields.find((e=>"__text"===e.name)),i=a.fields.find((e=>"__value"===e.name));if(s&&i)for(let e=0;e<s.values.length;e++)r.push({text:""+s.values.get(e),value:""+i.values.get(e)});else r.push(...a.fields.flatMap((e=>e.values.toArray())).map((e=>({text:e}))));return Array.from(new Set(r.map((e=>e.text)))).map((e=>{var t;return{text:e,value:null===(t=r.find((t=>t.text===e)))||void 0===t?void 0:t.value}}))}async transformAnnotationResponse(e,t){const a=(0,c.toDataQueryResponse)({data:t}).data;if(!a||!a.length)return[];const r=a[0],s=r.fields.find((e=>"time"===e.name));if(!s)throw new Error("Missing mandatory time column (with time column alias) in annotation query");const i=r.fields.find((e=>"timeend"===e.name)),n=r.fields.find((e=>"text"===e.name)),l=r.fields.find((e=>"tags"===e.name)),o=[];for(let t=0;t<r.length;t++){const a=i&&i.values.get(t)?Math.floor(i.values.get(t)):void 0;o.push({annotation:e.annotation,time:Math.floor(s.values.get(t)),timeEnd:a,text:n&&n.values.get(t)?n.values.get(t):"",tags:l&&l.values.get(t)?l.values.get(t).trim().split(/\s*,\s*/):[]})}return o}}function b(e,t,a){return t in e?Object.defineProperty(e,t,{value:a,enumerable:!0,configurable:!0,writable:!0}):e[t]=a,e}class S extends c.DataSourceWithBackend{constructor(e){let t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:(0,d.J)();super(e),b(this,"id",void 0),b(this,"name",void 0),b(this,"jsonData",void 0),b(this,"responseParser",void 0),b(this,"queryModel",void 0),b(this,"interval",void 0),b(this,"interpolateVariable",((e,t)=>{if("string"==typeof e)return t.multi||t.includeAll?this.queryModel.quoteLiteral(e):e;if("number"==typeof e)return e;return(0,s.map)(e,(e=>this.queryModel.quoteLiteral(e))).join(",")})),this.templateSrv=t,this.templateSrv=t,this.name=e.name,this.id=e.id,this.jsonData=e.jsonData,this.responseParser=new v,this.queryModel=new y({});const a=e.jsonData||{};this.interval=a.timeInterval||"1m"}interpolateVariablesInQueries(e,t){let a=e;return e&&e.length>0&&(a=e.map((e=>Object.assign({},e,{datasource:this.getRef(),rawSql:this.templateSrv.replace(e.rawSql,t,this.interpolateVariable),rawQuery:!0})))),a}filterQuery(e){return!e.hide}applyTemplateVariables(e,t){const a=new y(e,this.templateSrv,t);return{refId:e.refId,datasource:this.getRef(),rawSql:a.render(this.interpolateVariable),format:e.format}}async annotationQuery(e){if(!e.annotation.rawQuery)return Promise.reject({message:"Query missing in annotation definition"});const t={refId:e.annotation.name,datasource:this.getRef(),rawSql:this.templateSrv.replace(e.annotation.rawQuery,e.scopedVars,this.interpolateVariable),format:"table"};return(0,o.n)((0,c.getBackendSrv)().fetch({url:"/api/ds/query",method:"POST",data:{from:e.range.from.valueOf().toString(),to:e.range.to.valueOf().toString(),queries:[t]},requestId:e.annotation.name}).pipe((0,m.U)((async t=>await this.responseParser.transformAnnotationResponse(e,t.data)))))}metricFindQuery(e,t){var a,r,s,i;let n="tempvar";t&&t.variable&&t.variable.name&&(n=t.variable.name);const l=this.templateSrv.replace(e,(0,f._6)({query:e,wildcardChar:"%",options:t}),this.interpolateVariable),p={refId:n,datasource:this.getRef(),rawSql:l,format:"table"},d=null==t?void 0:t.range;return(0,o.n)((0,c.getBackendSrv)().fetch({url:"/api/ds/query",method:"POST",data:{from:null==d||null===(a=d.from)||void 0===a||null===(r=a.valueOf())||void 0===r?void 0:r.toString(),to:null==d||null===(s=d.to)||void 0===s||null===(i=s.valueOf())||void 0===i?void 0:i.toString(),queries:[p]},requestId:n}).pipe((0,m.U)((e=>this.responseParser.transformMetricFindResponse(e))),(0,h.K)((e=>(0,u.of)([])))))}_metaRequest(e){const t="meta",a={refId:t,datasource:this.getRef(),rawSql:e,format:"table"};return(0,c.getBackendSrv)().fetch({url:"/api/ds/query",method:"POST",data:{queries:[a]},requestId:t})}getVersion(){return(0,o.n)(this._metaRequest("SELECT current_setting('server_version_num')::int/100"))}getTimescaleDBVersion(){return(0,o.n)(this._metaRequest("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"))}testDatasource(){return(0,o.n)(this._metaRequest("SELECT 1")).then((()=>({status:"success",message:"Database Connection OK"}))).catch((e=>(0,p.Gw)(e)))}targetContainsTemplate(e){let t="";if(e.rawQuery)t=e.rawSql;else{t=new y(e).buildQuery()}return t=t.replace("$__",""),this.templateSrv.containsTemplate(t)}}var w=a("./public/app/core/app_events.ts"),_=a("./public/app/plugins/sdk.ts"),E=a("./public/app/types/events.ts");class C{constructor(e,t){this.target=e,this.queryModel=t,this.target=e,this.queryModel=t}getOperators(e){switch(e){case"float4":case"float8":return["=","!=","<","<=",">",">="];case"text":case"varchar":case"char":return["=","!=","<","<=",">",">=","IN","NOT IN","LIKE","NOT LIKE","~","~*","!~","!~*"];default:return["=","!=","<","<=",">",">=","IN","NOT IN"]}}quoteIdentAsLiteral(e){return this.queryModel.quoteLiteral(this.queryModel.unquoteIdentifier(e))}findMetricTable(){let e="\nSELECT\n\tquote_ident(table_name) as table_name,\n\t( SELECT\n\t    quote_ident(column_name) as column_name\n\t  FROM information_schema.columns c\n    WHERE\n      c.table_schema = t.table_schema AND\n      c.table_name = t.table_name AND\n      udt_name IN ('timestamptz','timestamp')\n    ORDER BY ordinal_position LIMIT 1\n  ) AS time_column,\n  ( SELECT\n      quote_ident(column_name) AS column_name\n    FROM information_schema.columns c\n    WHERE\n      c.table_schema = t.table_schema AND\n      c.table_name = t.table_name AND\n      udt_name='float8'\n    ORDER BY ordinal_position LIMIT 1\n  ) AS value_column\nFROM information_schema.tables t\nWHERE ";return e+=this.buildSchemaConstraint(),e+=" AND\n  EXISTS\n  ( SELECT 1\n    FROM information_schema.columns c\n    WHERE\n      c.table_schema = t.table_schema AND\n      c.table_name = t.table_name AND\n      udt_name IN ('timestamptz','timestamp')\n  ) AND\n  EXISTS\n  ( SELECT 1\n    FROM information_schema.columns c\n    WHERE\n      c.table_schema = t.table_schema AND\n      c.table_name = t.table_name AND\n      udt_name='float8'\n  )\nLIMIT 1\n;",e}buildSchemaConstraint(){return"\nquote_ident(table_schema) IN (\n  SELECT\n    CASE WHEN trim(s[i]) = '\"$user\"' THEN user ELSE trim(s[i]) END\n  FROM\n    generate_series(\n      array_lower(string_to_array(current_setting('search_path'),','),1),\n      array_upper(string_to_array(current_setting('search_path'),','),1)\n    ) as i,\n    string_to_array(current_setting('search_path'),',') s\n)"}buildTableConstraint(e){let t="";if(e.includes(".")){const a=e.split(".");return t="table_schema = "+this.quoteIdentAsLiteral(a[0]),t+=" AND table_name = "+this.quoteIdentAsLiteral(a[1]),t}return t=this.buildSchemaConstraint(),t+=" AND table_name = "+this.quoteIdentAsLiteral(e),t}buildTableQuery(){let e="SELECT quote_ident(table_name) FROM information_schema.tables WHERE ";return e+=this.buildSchemaConstraint(),e+=" ORDER BY table_name",e}buildColumnQuery(e){let t="SELECT quote_ident(column_name) FROM information_schema.columns WHERE ";switch(t+=this.buildTableConstraint(this.target.table),e){case"time":t+=" AND data_type IN ('timestamp without time zone','timestamp with time zone','bigint','integer','double precision','real')";break;case"metric":t+=" AND data_type IN ('text','character','character varying')";break;case"value":t+=" AND data_type IN ('bigint','integer','double precision','real','numeric')",t+=" AND column_name <> "+this.quoteIdentAsLiteral(this.target.timeColumn);break;case"group":t+=" AND data_type IN ('text','character','character varying','uuid')"}return t+=" ORDER BY column_name",t}buildValueQuery(e){let t="SELECT DISTINCT quote_literal("+e+")";return t+=" FROM "+this.target.table,t+=" WHERE $__timeFilter("+this.target.timeColumn+")",t+=" AND "+e+" IS NOT NULL",t+=" ORDER BY 1 LIMIT 100",t}buildDatatypeQuery(e){let t="SELECT udt_name FROM information_schema.columns WHERE ";return t+=this.buildTableConstraint(this.target.table),t+=" AND column_name = "+this.quoteIdentAsLiteral(e),t}buildAggregateQuery(){let e="SELECT DISTINCT proname FROM pg_aggregate ";return e+="INNER JOIN pg_proc ON pg_aggregate.aggfnoid = pg_proc.oid ",e+="INNER JOIN pg_type ON pg_type.oid=pg_proc.prorettype ",e+="WHERE pronargs=1 AND typname IN ('float8') AND aggkind='n' ORDER BY 1","SELECT DISTINCT proname FROM pg_aggregate INNER JOIN pg_proc ON pg_aggregate.aggfnoid = pg_proc.oid INNER JOIN pg_type ON pg_type.oid=pg_proc.prorettype WHERE pronargs=1 AND typname IN ('float8') AND aggkind='n' ORDER BY 1"}}var R=a("./public/app/angular/components/sql_part/sql_part.ts");const P=[];function x(e){P[e.type]=new R.m(e)}x({type:"column",style:"label",params:[{type:"column",dynamicLookup:!0}],defaultParams:["value"]}),x({type:"expression",style:"expression",label:"Expr:",params:[{name:"left",type:"string",dynamicLookup:!0},{name:"op",type:"string",dynamicLookup:!0},{name:"right",type:"string",dynamicLookup:!0}],defaultParams:["value","=","value"]}),x({type:"macro",style:"label",label:"Macro:",params:[],defaultParams:[]}),x({type:"aggregate",style:"label",params:[{name:"name",type:"string",options:[],baseOptions:["avg","count","min","max","sum","stddev","variance"],timescaleOptions:["first","last"]}],defaultParams:["avg"]}),x({type:"percentile",label:"Aggregate:",style:"label",params:[{name:"name",type:"string",options:["percentile_cont","percentile_disc"]},{name:"fraction",type:"number",options:["0.5","0.75","0.9","0.95","0.99"]}],defaultParams:["percentile_cont","0.95"]}),x({type:"alias",style:"label",params:[{name:"name",type:"string",quote:"double"}],defaultParams:["alias"]}),x({type:"time",style:"function",label:"time",params:[{name:"interval",type:"interval",options:["$__interval","1s","10s","1m","5m","10m","15m","1h"]},{name:"fill",type:"string",options:["none","NULL","previous","0"]}],defaultParams:["$__interval","none"]}),x({type:"window",style:"label",params:[{name:"function",type:"string",options:["delta","increase","rate","sum"]}],defaultParams:["increase"]}),x({type:"moving_window",style:"label",label:"Moving Window:",params:[{name:"function",type:"string",options:["avg"]},{name:"window_size",type:"number",options:["3","5","7","10","20"]}],defaultParams:["avg","5"]});const A={create:function(e){const t=P[e.type];return t?new R.H(e,t):null}};function T(e,t,a){return t in e?Object.defineProperty(e,t,{value:a,enumerable:!0,configurable:!0,writable:!0}):e[t]=a,e}class q extends _.QueryCtrl{constructor(e,t,a,s){super(e,t),T(this,"formats",void 0),T(this,"queryModel",void 0),T(this,"metaBuilder",void 0),T(this,"lastQueryMeta",void 0),T(this,"lastQueryError",void 0),T(this,"showHelp",!1),T(this,"tableSegment",void 0),T(this,"whereAdd",void 0),T(this,"timeColumnSegment",void 0),T(this,"metricColumnSegment",void 0),T(this,"selectMenu",[]),T(this,"selectParts",[[]]),T(this,"groupParts",[]),T(this,"whereParts",[]),T(this,"groupAdd",void 0),this.templateSrv=a,this.uiSegmentSrv=s,this.templateSrv=a,this.uiSegmentSrv=s,this.target=this.target,this.queryModel=new y(this.target,a,this.panel.scopedVars),this.metaBuilder=new C(this.target,this.queryModel),this.updateProjection(),this.formats=[{text:"Time series",value:"time_series"},{text:"Table",value:"table"}],this.target.rawSql||("table"===this.panelCtrl.panel.type?(this.target.format="table",this.target.rawSql="SELECT 1",this.target.rawQuery=!0):(this.target.rawSql="SELECT\n  $__time(time_column),\n  value1\nFROM\n  metric_table\nWHERE\n  $__timeFilter(time_column)\n",this.datasource.metricFindQuery(this.metaBuilder.findMetricTable()).then((e=>{if(e.length>0){this.target.table=e[0].text;let t=this.uiSegmentSrv.newSegment(this.target.table);this.tableSegment.html=t.html,this.tableSegment.value=t.value,this.target.timeColumn=e[1].text,t=this.uiSegmentSrv.newSegment(this.target.timeColumn),this.timeColumnSegment.html=t.html,this.timeColumnSegment.value=t.value,this.target.timeColumnType="timestamp",this.target.select=[[{type:"column",params:[e[2].text]}]],this.updateProjection(),this.updateRawSqlAndRefresh()}})))),this.target.table?this.tableSegment=s.newSegment(this.target.table):this.tableSegment=s.newSegment({value:"select table",fake:!0}),this.timeColumnSegment=s.newSegment(this.target.timeColumn),this.metricColumnSegment=s.newSegment(this.target.metricColumn),this.buildSelectMenu(),this.whereAdd=this.uiSegmentSrv.newPlusButton(),this.groupAdd=this.uiSegmentSrv.newPlusButton(),this.panelCtrl.events.on(r.PanelEvents.dataReceived,this.onDataReceived.bind(this),e),this.panelCtrl.events.on(r.PanelEvents.dataError,this.onDataError.bind(this),e)}updateRawSqlAndRefresh(){this.target.rawQuery||(this.target.rawSql=this.queryModel.buildQuery()),this.panelCtrl.refresh()}timescaleAggCheck(){const e=this.findAggregateIndex(this.selectParts[0]);if(-1!==e){const t=this.selectParts[0][e].def.params[0].baseOptions,a=t.concat(this.selectParts[0][e].def.params[0].timescaleOptions);!0===this.datasource.jsonData.timescaledb?this.selectParts[0][e].def.params[0].options=a:this.selectParts[0][e].def.params[0].options=t}}updateProjection(){this.selectParts=(0,s.map)(this.target.select,(e=>(0,s.map)(e,A.create).filter((e=>e)))),this.timescaleAggCheck(),this.whereParts=(0,s.map)(this.target.where,A.create).filter((e=>e)),this.groupParts=(0,s.map)(this.target.group,A.create).filter((e=>e))}updatePersistedParts(){this.target.select=(0,s.map)(this.selectParts,(e=>(0,s.map)(e,(e=>({type:e.def.type,datatype:e.datatype,params:e.params}))))),this.timescaleAggCheck(),this.target.where=(0,s.map)(this.whereParts,(e=>({type:e.def.type,datatype:e.datatype,name:e.name,params:e.params}))),this.target.group=(0,s.map)(this.groupParts,(e=>({type:e.def.type,datatype:e.datatype,params:e.params})))}buildSelectMenu(){this.selectMenu=[];const e={text:"Aggregate Functions",value:"aggregate",submenu:[{text:"Average",value:"avg"},{text:"Count",value:"count"},{text:"Maximum",value:"max"},{text:"Minimum",value:"min"},{text:"Sum",value:"sum"},{text:"Standard deviation",value:"stddev"},{text:"Variance",value:"variance"}]};if(!0===this.datasource.jsonData.timescaledb&&(e.submenu.push({text:"First",value:"first"}),e.submenu.push({text:"Last",value:"last"})),this.selectMenu.push(e),this.datasource.jsonData.postgresVersion>=904){const e={text:"Ordered-Set Aggregate Functions",value:"percentile",submenu:[{text:"Percentile (continuous)",value:"percentile_cont"},{text:"Percentile (discrete)",value:"percentile_disc"}]};this.selectMenu.push(e)}this.selectMenu.push({text:"Window Functions",value:"window",submenu:[{text:"Delta",value:"delta"},{text:"Increase",value:"increase"},{text:"Rate",value:"rate"},{text:"Sum",value:"sum"},{text:"Moving Average",value:"avg",type:"moving_window"}]}),this.selectMenu.push({text:"Alias",value:"alias"}),this.selectMenu.push({text:"Column",value:"column"})}toggleEditorMode(){this.target.rawQuery?w.Z.publish(new E.VJ({title:"Warning",text2:"Switching to query builder may overwrite your raw SQL.",icon:"exclamation-triangle",yesText:"Switch",onConfirm:()=>{this.$scope.$evalAsync((()=>{this.target.rawQuery=!this.target.rawQuery}))}})):this.$scope.$evalAsync((()=>{this.target.rawQuery=!this.target.rawQuery}))}resetPlusButton(e){const t=this.uiSegmentSrv.newPlusButton();e.html=t.html,e.value=t.value,e.type=t.type,e.fake=t.fake}getTableSegments(){return this.datasource.metricFindQuery(this.metaBuilder.buildTableQuery()).then(this.transformToSegments({})).catch(this.handleQueryError.bind(this))}tableChanged(){this.target.table=this.tableSegment.value,this.target.where=[],this.target.group=[],this.updateProjection();const e=this.uiSegmentSrv.newSegment("none");this.metricColumnSegment.html=e.html,this.metricColumnSegment.value=e.value,this.target.metricColumn="none";const t=this.datasource.metricFindQuery(this.metaBuilder.buildColumnQuery("time")).then((e=>{if(e.length>0&&!(0,s.find)(e,(e=>e.text===this.target.timeColumn))){const t=this.uiSegmentSrv.newSegment(e[0].text);this.timeColumnSegment.html=t.html,this.timeColumnSegment.value=t.value}return this.timeColumnChanged(!1)})),a=this.datasource.metricFindQuery(this.metaBuilder.buildColumnQuery("value")).then((e=>{e.length>0&&(this.target.select=[[{type:"column",params:[e[0].text]}]],this.updateProjection())}));Promise.all([t,a]).then((()=>{this.updateRawSqlAndRefresh()}))}getTimeColumnSegments(){return this.datasource.metricFindQuery(this.metaBuilder.buildColumnQuery("time")).then(this.transformToSegments({})).catch(this.handleQueryError.bind(this))}timeColumnChanged(e){return this.target.timeColumn=this.timeColumnSegment.value,this.datasource.metricFindQuery(this.metaBuilder.buildDatatypeQuery(this.target.timeColumn)).then((t=>{if(1===t.length){let e;this.target.timeColumnType!==t[0].text&&(this.target.timeColumnType=t[0].text),e=this.queryModel.hasUnixEpochTimecolumn()?A.create({type:"macro",name:"$__unixEpochFilter",params:[]}):A.create({type:"macro",name:"$__timeFilter",params:[]}),this.whereParts.length>=1&&"macro"===this.whereParts[0].def.type?this.whereParts[0]=e:this.whereParts.splice(0,0,e)}this.updatePersistedParts(),!1!==e&&this.updateRawSqlAndRefresh()}))}getMetricColumnSegments(){return this.datasource.metricFindQuery(this.metaBuilder.buildColumnQuery("metric")).then(this.transformToSegments({addNone:!0})).catch(this.handleQueryError.bind(this))}metricColumnChanged(){this.target.metricColumn=this.metricColumnSegment.value,this.updateRawSqlAndRefresh()}onDataReceived(e){var t;this.lastQueryError=void 0,this.lastQueryMeta=null===(t=e[0])||void 0===t?void 0:t.meta}onDataError(e){if(e.data&&e.data.results){const t=e.data.results[this.target.refId];t&&(this.lastQueryError=t.error)}}transformToSegments(e){return t=>{const a=(0,s.map)(t,(e=>this.uiSegmentSrv.newSegment({value:e.text,expandable:e.expandable})));if(e.addTemplateVars)for(const t of this.templateSrv.getVariables()){let r;r="$"+t.name,e.templateQuoter&&!1===t.multi&&(r=e.templateQuoter(r)),a.unshift(this.uiSegmentSrv.newSegment({type:"template",value:r,expandable:!0}))}return e.addNone&&a.unshift(this.uiSegmentSrv.newSegment({type:"template",value:"none",expandable:!0})),a}}findAggregateIndex(e){return(0,s.findIndex)(e,(e=>"aggregate"===e.def.type||"percentile"===e.def.type))}findWindowIndex(e){return(0,s.findIndex)(e,(e=>"window"===e.def.type||"moving_window"===e.def.type))}addSelectPart(e,t,a){let r=t.value;a&&a.type&&(r=a.type);let i=A.create({type:r});a&&(i.params[0]=a.value);let n=!1;switch(r){case"column":const t=(0,s.map)(e,(e=>A.create({type:e.def.type,params:(0,s.clone)(e.params)})));this.selectParts.push(t);break;case"percentile":case"aggregate":0===this.target.group.length&&this.addGroup("time","$__interval");const a=this.findAggregateIndex(e);-1!==a?e[a]=i:e.splice(1,0,i),(0,s.find)(e,(e=>"alias"===e.def.type))||(n=!0);break;case"moving_window":case"window":const r=this.findWindowIndex(e);if(-1!==r)e[r]=i;else{const t=this.findAggregateIndex(e);-1!==t?e.splice(t+1,0,i):e.splice(1,0,i)}(0,s.find)(e,(e=>"alias"===e.def.type))||(n=!0);break;case"alias":n=!0}n&&(i=A.create({type:"alias",params:[e[0].params[0].replace(/"/g,"")]}),"alias"===e[e.length-1].def.type?e[e.length-1]=i:e.push(i)),this.updatePersistedParts(),this.updateRawSqlAndRefresh()}removeSelectPart(e,t){if("column"===t.def.type){if(this.selectParts.length>1){const t=(0,s.indexOf)(this.selectParts,e);this.selectParts.splice(t,1)}}else{const a=(0,s.indexOf)(e,t);e.splice(a,1)}this.updatePersistedParts()}handleSelectPartEvent(e,t,a){switch(a.name){case"get-param-options":switch(t.def.type){case"aggregate":return this.datasource.metricFindQuery(this.metaBuilder.buildAggregateQuery()).then(this.transformToSegments({})).catch(this.handleQueryError.bind(this));case"column":return this.datasource.metricFindQuery(this.metaBuilder.buildColumnQuery("value")).then(this.transformToSegments({})).catch(this.handleQueryError.bind(this))}case"part-param-changed":this.updatePersistedParts(),this.updateRawSqlAndRefresh();break;case"action":this.removeSelectPart(e,t),this.updateRawSqlAndRefresh();break;case"get-part-actions":return Promise.resolve([{text:"Remove",value:"remove-part"}])}}handleGroupPartEvent(e,t,a){switch(a.name){case"get-param-options":return this.datasource.metricFindQuery(this.metaBuilder.buildColumnQuery()).then(this.transformToSegments({})).catch(this.handleQueryError.bind(this));case"part-param-changed":this.updatePersistedParts(),this.updateRawSqlAndRefresh();break;case"action":this.removeGroup(e,t),this.updateRawSqlAndRefresh();break;case"get-part-actions":return Promise.resolve([{text:"Remove",value:"remove-part"}])}}addGroup(e,t){let a=[t];"time"===e&&(a=["$__interval","none"]);const r=A.create({type:e,params:a});"time"===e?this.groupParts.splice(0,0,r):this.groupParts.push(r);for(const e of this.selectParts)if(!e.some((e=>"aggregate"===e.def.type))){const t=A.create({type:"aggregate",params:["avg"]});if(e.splice(1,0,t),!e.some((e=>"alias"===e.def.type))){const t=A.create({type:"alias",params:[e[0].part.params[0]]});e.push(t)}}this.updatePersistedParts()}removeGroup(e,t){"time"===e.def.type&&(this.selectParts=(0,s.map)(this.selectParts,(e=>(0,s.filter)(e,(e=>"aggregate"!==e.def.type&&"percentile"!==e.def.type))))),this.groupParts.splice(t,1),this.updatePersistedParts()}handleWherePartEvent(e,t,a,r){switch(a.name){case"get-param-options":switch(a.param.name){case"left":return this.datasource.metricFindQuery(this.metaBuilder.buildColumnQuery()).then(this.transformToSegments({})).catch(this.handleQueryError.bind(this));case"right":return["int4","int8","float4","float8","timestamp","timestamptz"].indexOf(t.datatype)>-1?Promise.resolve([]):this.datasource.metricFindQuery(this.metaBuilder.buildValueQuery(t.params[0])).then(this.transformToSegments({addTemplateVars:!0,templateQuoter:e=>this.queryModel.quoteLiteral(e)})).catch(this.handleQueryError.bind(this));case"op":return Promise.resolve(this.uiSegmentSrv.newOperators(this.metaBuilder.getOperators(t.datatype)));default:return Promise.resolve([])}case"part-param-changed":this.updatePersistedParts(),this.datasource.metricFindQuery(this.metaBuilder.buildDatatypeQuery(t.params[0])).then((e=>{1===e.length&&(t.datatype=e[0].text)})),this.updateRawSqlAndRefresh();break;case"action":e.splice(r,1),this.updatePersistedParts(),this.updateRawSqlAndRefresh();break;case"get-part-actions":return Promise.resolve([{text:"Remove",value:"remove-part"}])}}getWhereOptions(){const e=[];return this.queryModel.hasUnixEpochTimecolumn()?e.push(this.uiSegmentSrv.newSegment({type:"macro",value:"$__unixEpochFilter"})):e.push(this.uiSegmentSrv.newSegment({type:"macro",value:"$__timeFilter"})),e.push(this.uiSegmentSrv.newSegment({type:"expression",value:"Expression"})),Promise.resolve(e)}addWhereAction(e,t){switch(this.whereAdd.type){case"macro":{const e=A.create({type:"macro",name:this.whereAdd.value,params:[]});this.whereParts.length>=1&&"macro"===this.whereParts[0].def.type?this.whereParts[0]=e:this.whereParts.splice(0,0,e);break}default:this.whereParts.push(A.create({type:"expression",params:["value","=","value"]}))}this.updatePersistedParts(),this.resetPlusButton(this.whereAdd),this.updateRawSqlAndRefresh()}getGroupOptions(){return this.datasource.metricFindQuery(this.metaBuilder.buildColumnQuery("group")).then((e=>{const t=[];this.queryModel.hasTimeGroup()||t.push(this.uiSegmentSrv.newSegment({type:"time",value:"time($__interval,none)"}));for(const a of e)t.push(this.uiSegmentSrv.newSegment({type:"column",value:a.text}));return t})).catch(this.handleQueryError.bind(this))}addGroupAction(){this.addGroup(this.groupAdd.type,this.groupAdd.value),this.resetPlusButton(this.groupAdd),this.updateRawSqlAndRefresh()}handleQueryError(e){return this.error=e.message||"Failed to issue metric query",[]}}q.$inject=["$scope","$injector","templateSrv","uiSegmentSrv"],T(q,"templateUrl","partials/query.editor.html");class D{constructor(e){this.annotation=e.ctrl.annotation,this.annotation.rawQuery=this.annotation.rawQuery||"SELECT\n  extract(epoch from time_column) AS time,\n  text_column as text,\n  tags_column as tags\nFROM\n  metric_table\nWHERE\n  $__timeFilter(time_column)\n"}}var Q,N,I;D.$inject=["$scope"],I="partials/annotations.editor.html",(N="templateUrl")in(Q=D)?Object.defineProperty(Q,N,{value:I,enumerable:!0,configurable:!0,writable:!0}):Q[N]=I;const M=new r.DataSourcePlugin(S).setQueryCtrl(q).setConfigCtrl(l).setAnnotationQueryCtrl(D)}}]);
//# sourceMappingURL=postgresPlugin.d32aef4f2822e56fb2d6.js.map