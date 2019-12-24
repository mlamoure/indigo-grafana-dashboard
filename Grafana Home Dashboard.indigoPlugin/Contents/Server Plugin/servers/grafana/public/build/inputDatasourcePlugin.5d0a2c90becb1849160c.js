(window.webpackJsonp=window.webpackJsonp||[]).push([[35],{sz7o:function(e,t,a){"use strict";a.r(t);var r=a("Obii"),n=a("mrSG"),s=function(e){function t(t){var a=e.call(this,t)||this;return a.data=[],t.jsonData.data&&(a.data=t.jsonData.data.map(function(e){return Object(r.toDataFrame)(e)})),a}return Object(n.__extends)(t,e),t.prototype.getQueryDisplayText=function(e){return e.data?"Panel Data: "+i(e.data):"Shared Data From: "+this.name+" ("+i(this.data)+")"},t.prototype.metricFindQuery=function(e,t){var a=this;return new Promise(function(e,t){var r,s,o,i,l=[];try{for(var u=Object(n.__values)(a.data),c=u.next();!c.done;c=u.next()){var d=c.value;try{for(var f=(o=void 0,Object(n.__values)(d.fields)),h=f.next();!h.done;h=f.next()){var p=h.value;l.push({text:p.name})}}catch(e){o={error:e}}finally{try{h&&!h.done&&(i=f.return)&&i.call(f)}finally{if(o)throw o.error}}}}catch(e){r={error:e}}finally{try{c&&!c.done&&(s=u.return)&&s.call(u)}finally{if(r)throw r.error}}e(l)})},t.prototype.query=function(e){var t,a,s=[];try{for(var o=Object(n.__values)(e.targets),i=o.next();!i.done;i=o.next()){var l=i.value;if(!l.hide){var u=this.data;l.data&&(u=l.data.map(function(e){return Object(r.toDataFrame)(e)}));for(var c=0;c<u.length;c++)s.push(Object(n.__assign)(Object(n.__assign)({},u[c]),{refId:l.refId}))}}}catch(e){t={error:e}}finally{try{i&&!i.done&&(a=o.return)&&a.call(o)}finally{if(t)throw t.error}}return Promise.resolve({data:s})},t.prototype.testDatasource=function(){var e=this;return new Promise(function(t,a){var r,s,o=0,i=e.data.length+" Series:";try{for(var l=Object(n.__values)(e.data),u=l.next();!u.done;u=l.next()){var c=u.value,d=c.length;i+=" ["+c.fields.length+" Fields, "+d+" Rows]",o+=d}}catch(e){r={error:e}}finally{try{u&&!u.done&&(s=l.return)&&s.call(l)}finally{if(r)throw r.error}}o>0&&t({status:"success",message:i}),a({status:"error",message:"No Data Entered"})})},t}(r.DataSourceApi);function o(e){return e&&e.fields&&e.fields.length?e.hasOwnProperty("length")?e.length:e.fields[0].values.length:0}function i(e){if(!e||!e.length)return"";if(e.length>1){var t=e.reduce(function(e,t){return e+o(t)},0);return e.length+" Series, "+t+" Rows"}var a=e[0];if(!a.fields)return"Missing Fields";var r=o(a);return a.fields.length+" Fields, "+r+" Rows"}var l=a("q1tI"),u=a.n(l),c=a("kDLi");function d(e){return e&&e.length?Object(r.toCSV)(e.map(function(e){return Object(r.toDataFrame)(e)})):""}var f=[{value:"panel",label:"Panel",description:"Save data in the panel configuration."},{value:"shared",label:"Shared",description:"Save data in the shared datasource object."}],h=function(e){function t(){var t=null!==e&&e.apply(this,arguments)||this;return t.state={text:""},t.onSourceChange=function(e){var a=t.props,s=a.datasource,o=a.query,i=a.onChange,l=a.onRunQuery,u=void 0;if("panel"===e.value){if(o.data)return;(u=Object(n.__spread)(s.data))||(u=[new r.MutableDataFrame]),t.setState({text:Object(r.toCSV)(u)})}i(Object(n.__assign)(Object(n.__assign)({},o),{data:u})),l()},t.onSeriesParsed=function(e,a){var s=t.props,o=s.query,i=s.onChange,l=s.onRunQuery;t.setState({text:a}),e||(e=[new r.MutableDataFrame]),i(Object(n.__assign)(Object(n.__assign)({},o),{data:e})),l()},t}return Object(n.__extends)(t,e),t.prototype.onComponentDidMount=function(){var e=d(this.props.query.data);this.setState({text:e})},t.prototype.render=function(){var e=this.props,t=e.datasource,a=e.query,r=t.id,n=t.name,s=this.state.text,o=a.data?f[0]:f[1];return u.a.createElement("div",null,u.a.createElement("div",{className:"gf-form"},u.a.createElement(c.FormLabel,{width:4},"Data"),u.a.createElement(c.Select,{width:6,options:f,value:o,onChange:this.onSourceChange}),u.a.createElement("div",{className:"btn btn-link"},a.data?i(a.data):u.a.createElement("a",{href:"datasources/edit/"+r+"/"},n,": ",i(t.data),"   ",u.a.createElement("i",{className:"fa fa-pencil-square-o"})))),a.data&&u.a.createElement(c.TableInputCSV,{text:s,onSeriesParsed:this.onSeriesParsed,width:"100%",height:200}))},t}(l.PureComponent),p=function(e){function t(){var t=null!==e&&e.apply(this,arguments)||this;return t.state={text:""},t.onSeriesParsed=function(e,a){var s=t.props,o=s.options,i=s.onOptionsChange;e||(e=[new r.MutableDataFrame]);var l=Object(n.__assign)(Object(n.__assign)({},o.jsonData),{data:e});i(Object(n.__assign)(Object(n.__assign)({},o),{jsonData:l})),t.setState({text:a})},t}return Object(n.__extends)(t,e),t.prototype.componentDidMount=function(){var e=this.props.options;if(e.jsonData.data){var t=d(e.jsonData.data);this.setState({text:t})}},t.prototype.render=function(){var e=this.state.text;return u.a.createElement("div",null,u.a.createElement("div",{className:"gf-form-group"},u.a.createElement("h4",null,"Shared Data:"),u.a.createElement("span",null,"Enter CSV"),u.a.createElement(c.TableInputCSV,{text:e,onSeriesParsed:this.onSeriesParsed,width:"100%",height:200})),u.a.createElement("div",{className:"grafana-info-box"},"This data is stored in the datasource json and is returned to every user in the initial request for any datasource. This is an appropriate place to enter a few values. Large datasets will perform better in other datasources.",u.a.createElement("br",null),u.a.createElement("br",null),u.a.createElement("b",null,"NOTE:")," Changes to this data will only be reflected after a browser refresh."))},t}(l.PureComponent);a.d(t,"plugin",function(){return v});var v=new r.DataSourcePlugin(s).setConfigEditor(p).setQueryEditor(h)}}]);
//# sourceMappingURL=inputDatasourcePlugin.5d0a2c90becb1849160c.js.map