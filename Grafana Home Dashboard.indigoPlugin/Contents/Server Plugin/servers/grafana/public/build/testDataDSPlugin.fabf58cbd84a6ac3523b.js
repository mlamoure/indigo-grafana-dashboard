(window.webpackJsonp=window.webpackJsonp||[]).push([[47],{RQDA:function(e,t,r){"use strict";r.r(t);var a=r("Obii"),n=r("mrSG"),i=r("NXk7");function o(e){return function e(t,r,a){var i,o,s,u;if(a>=r.length)return t;if("*"===r[a])return t;var l=r[a],c=[],d=[l];l.startsWith("{")&&(d=l.replace(/\{|\}/g,"").split(","));try{for(var f=Object(n.__values)(t),p=f.next();!p.done;p=f.next()){var m=p.value;try{for(var h=(s=void 0,Object(n.__values)(d)),v=h.next();!v.done;v=h.next()){var g=v.value;if(-1!==g.indexOf("*")){var y=g.replace("*","");new RegExp("^"+y+".*","gi").test(m.name)&&(c=c.concat(e([m],r,a+1)))}else m.name===g&&(c=c.concat(e(m.children,r,a+1)))}}catch(e){s={error:e}}finally{try{v&&!v.done&&(u=h.return)&&u.call(h)}finally{if(s)throw s.error}}}}catch(e){i={error:e}}finally{try{p&&!p.done&&(o=f.return)&&o.call(f)}finally{if(i)throw i.error}}return c}(function e(t,r){var a,i,o=[];if(r>3)return[];try{for(var s=Object(n.__values)(["A","B","C"]),u=s.next();!u.done;u=s.next()){var l=""+t+u.value;o.push({name:l,children:e(l,r+1)})}}catch(e){a={error:e}}finally{try{u&&!u.done&&(i=s.return)&&i.call(s)}finally{if(a)throw a.error}}return o}("",0),e.split("."),0)}var s=r("0/uQ"),u=r("p0ib"),l=r("LvDl"),c=r.n(l),d=r("6blF"),f=0;function p(){return f=(f+Math.floor(5*Math.random()))%m.length,m[f]}var m=["At","vero","eos","et","accusamus","et","iusto","odio","dignissimos","ducimus","qui","blanditiis","praesentium","voluptatum","deleniti","atque","corrupti","quos","dolores","et","quas","molestias","excepturi","sint","occaecati","cupiditate","non","provident","similique","sunt","in","culpa","qui","officia","deserunt","mollitia","animi","id","est","laborum","et","dolorum","fuga","Et","harum","quidem","rerum","facilis","est","et","expedita","distinctio","Nam","libero","tempore","cum","soluta","nobis","est","eligendi","optio","cumque","nihil","impedit","quo","minus","id","quod","maxime","placeat","facere","possimus","omnis","voluptas","assumenda","est","omnis","dolor","repellendus","Temporibus","autem","quibusdam","et","aut","officiis","debitis","aut","rerum","necessitatibus","saepe","eveniet","ut","et","voluptates","repudiandae","sint","et","molestiae","non","recusandae","Itaque","earum","rerum","hic","tenetur","a","sapiente","delectus","ut","aut","reiciendis","voluptatibus","maiores","alias","consequatur","aut","perferendis","doloribus","asperiores","repellat"],h={type:"signal",speed:250,spread:3.5,noise:2.2,bands:1};function v(e,t){var r=Object(l.defaults)(e.stream,h);if("signal"===r.type)return function(e,t,r){return new d.a(function(n){var i="signal-"+r.panelId+"-"+e.refId,o=r.maxDataPoints||1e3,s=new a.CircularDataFrame({append:"tail",capacity:o});s.refId=e.refId,s.name=e.alias||"Signal "+e.refId,s.addField({name:"time",type:a.FieldType.time}),s.addField({name:"value",type:a.FieldType.number});for(var u=t.spread,l=t.speed,c=t.bands,d=t.noise,f=0;f<c;f++){var p=c>1?" "+(f+1):"";s.addField({name:"Min"+p,type:a.FieldType.number}),s.addField({name:"Max"+p,type:a.FieldType.number})}for(var m=100*Math.random(),h=null,v=function(e){m+=(Math.random()-.5)*u;var t=0;s.fields[t++].values.add(e),s.fields[t++].values.add(m);for(var r=m,a=m,n=0;n<c;n++)r-=Math.random()*d,a+=Math.random()*d,s.fields[t++].values.add(r),s.fields[t++].values.add(a)},g=Date.now()-o*l,f=0;f<o;f++)v(g),g+=l;var y=function(){v(Date.now()),n.next({data:[s],key:i}),h=setTimeout(y,l)};return setTimeout(y,5),function(){console.log("unsubscribing to stream "+i),clearTimeout(h)}})}(e,r,t);if("logs"===r.type)return function(e,t,r){return new d.a(function(n){var i="logs-"+r.panelId+"-"+e.refId,o=r.maxDataPoints||1e3,s=new a.CircularDataFrame({append:"tail",capacity:o});s.refId=e.refId,s.name=e.alias||"Logs "+e.refId,s.addField({name:"time",type:a.FieldType.time}),s.addField({name:"line",type:a.FieldType.string});var u=t.speed,l=null,c=function(){s.values.time.add(Date.now()),s.values.line.add(function(e){void 0===e&&(e=60);for(var t=p();t.length<e;)t+=" "+p();return t}()),n.next({data:[s],key:i}),l=setTimeout(c,u)};return setTimeout(c,5),function(){console.log("unsubscribing to stream "+i),clearTimeout(l)}})}(e,r,t);if("fetch"===r.type)return function(e,t,r){return new d.a(function(i){var o,s="fetch-"+r.panelId+"-"+e.refId,u=r.maxDataPoints||1e3,l=new a.CircularDataFrame({append:"tail",capacity:u});l.refId=e.refId,l.name=e.alias||"Fetch "+e.refId;var c=new a.CSVReader({callback:{onHeader:function(t){var r,i;l.fields.length&&((l=new a.CircularDataFrame({append:"tail",capacity:u})).refId=e.refId,l.name="Fetch "+e.refId);try{for(var o=Object(n.__values)(t),s=o.next();!s.done;s=o.next()){var c=s.value;l.addField(c)}}catch(e){r={error:e}}finally{try{s&&!s.done&&(i=o.return)&&i.call(o)}finally{if(r)throw r.error}}},onRow:function(e){l.add(e)}}}),d=function(e){if(e.value){var t=(new TextDecoder).decode(e.value);c.readCSV(t)}return i.next({data:[l],key:s,state:e.done?a.LoadingState.Done:a.LoadingState.Streaming}),e.done?(console.log("Finished stream"),void i.complete()):o.read().then(d)};return fetch(new Request(t.url)).then(function(e){(o=e.body.getReader()).read().then(d)}),function(){console.log("unsubscribing to stream "+s)}})}(e,r,t);throw new Error("Unknown Stream Type: "+r.type)}var g=r("5kRJ"),y=r("4qJB"),b=function(e){function t(t){return e.call(this,t)||this}return Object(n.__extends)(t,e),t.prototype.query=function(e){var t,r,a=this,o=[],l=[];try{for(var c=Object(n.__values)(e.targets),d=c.next();!d.done;d=c.next()){var f=d.value;f.hide||("streaming_client"===f.scenarioId?l.push(v(f,e)):o.push(Object(n.__assign)(Object(n.__assign)({},f),{intervalMs:e.intervalMs,maxDataPoints:e.maxDataPoints,datasourceId:this.id,alias:g.b.replace(f.alias||"")})))}}catch(e){t={error:e}}finally{try{d&&!d.done&&(r=c.return)&&r.call(c)}finally{if(t)throw t.error}}if(o.length){var p=Object(i.b)().datasourceRequest({method:"POST",url:"/api/tsdb/query",data:{from:e.range.from.valueOf().toString(),to:e.range.to.valueOf().toString(),queries:o},requestId:e.requestId}).then(function(e){return a.processQueryResult(o,e)});l.push(Object(s.a)(p))}return u.a.apply(void 0,Object(n.__spread)(l))},t.prototype.processQueryResult=function(e,t){var r,a,i,o,s,u,l=[],c=void 0;try{for(var d=Object(n.__values)(e),f=d.next();!f.done;f=d.next()){var p=f.value,m=t.data.results[p.refId];try{for(var h=(i=void 0,Object(n.__values)(m.tables||[])),v=h.next();!v.done;v=h.next()){var g=v.value;g.refId=p.refId,g.name=p.alias,l.push(g)}}catch(e){i={error:e}}finally{try{v&&!v.done&&(o=h.return)&&o.call(h)}finally{if(i)throw i.error}}try{for(var y=(s=void 0,Object(n.__values)(m.series||[])),b=y.next();!b.done;b=y.next()){var w=b.value;l.push({target:w.name,datapoints:w.points,refId:p.refId,tags:w.tags})}}catch(e){s={error:e}}finally{try{b&&!b.done&&(u=y.return)&&u.call(y)}finally{if(s)throw s.error}}m.error&&(c={message:m.error})}}catch(e){r={error:e}}finally{try{f&&!f.done&&(a=d.return)&&a.call(d)}finally{if(r)throw r.error}}return{data:l,error:c}},t.prototype.annotationQuery=function(e){for(var t=e.range.from.valueOf(),r=[],a=(e.range.to.valueOf()-t)/10,n=0;n<10;n++)r.push({annotation:e.annotation,time:t,text:'This is the text, <a href="https://grafana.com">Grafana.com</a>',tags:["text","server"]}),t+=a;return Promise.resolve(r)},t.prototype.getQueryDisplayText=function(e){return e.alias?e.scenarioId+" as "+e.alias:e.scenarioId},t.prototype.testDatasource=function(){return Promise.resolve({status:"success",message:"Data source is working"})},t.prototype.getScenarios=function(){return Object(i.b)().get("/api/tsdb/testdata/scenarios")},t.prototype.metricFindQuery=function(e,t){return new Promise(function(r,a){setTimeout(function(){var a=o(g.b.replace(e,Object(y.g)({query:e,wildcardChar:"*",options:t}))).map(function(e){return{value:e.name,text:e.name}});r(a)},100)})},t}(a.DataSourceApi),w=r("LzXI"),I={timeStep:60,onCount:3,onValue:2,offCount:3,offValue:1},x={timeStep:60,valuesCSV:"0,0,2,2,1,1"},_=["random_walk","predictable_pulse","predictable_csv_wave"],O=function(e){function t(t,r){var n=e.call(this,t,r)||this;return n.showLabels=!1,n.target.scenarioId=n.target.scenarioId||"random_walk",n.scenarioList=[],n.newPointTime=Object(a.dateTime)(),n.selectedPoint={text:"Select point",value:null},n.showLabels=_.includes(n.target.scenarioId),n}return t.$inject=["$scope","$injector"],Object(n.__extends)(t,e),t.prototype.getPoints=function(){return c.a.map(this.target.points,function(e,t){return{text:Object(a.dateTime)(e[1]).format("MMMM Do YYYY, H:mm:ss")+" : "+e[0],value:t}})},t.prototype.pointSelected=function(e){this.selectedPoint=e},t.prototype.deletePoint=function(){this.target.points.splice(this.selectedPoint.value,1),this.selectedPoint={text:"Select point",value:null},this.refresh()},t.prototype.addPoint=function(){this.target.points=this.target.points||[],this.newPointTime=a.dateMath.parse(this.newPointTime),this.target.points.push([this.newPointValue,this.newPointTime.valueOf()]),this.target.points=c.a.sortBy(this.target.points,function(e){return e[1]}),this.refresh()},t.prototype.$onInit=function(){var e=this;return Object(i.b)().get("/api/tsdb/testdata/scenarios").then(function(t){e.scenarioList=t,e.scenario=c.a.find(e.scenarioList,{id:e.target.scenarioId})})},t.prototype.scenarioChanged=function(){this.scenario=c.a.find(this.scenarioList,{id:this.target.scenarioId}),this.target.stringInput=this.scenario.stringInput,this.showLabels=_.includes(this.target.scenarioId),"manual_entry"===this.target.scenarioId?this.target.points=this.target.points||[]:delete this.target.points,"streaming_client"===this.target.scenarioId?this.target.stream=c.a.defaults(this.target.stream||{},h):delete this.target.stream,"predictable_pulse"===this.target.scenarioId?this.target.pulseWave=c.a.defaults(this.target.pulseWave||{},I):delete this.target.pulseWave,"predictable_csv_wave"===this.target.scenarioId?this.target.csvWave=c.a.defaults(this.target.csvWave||{},x):delete this.target.csvWave,this.refresh()},t.prototype.streamChanged=function(){this.refresh()},t.templateUrl="partials/query.editor.html",t}(w.QueryCtrl),j=r("q1tI"),P=r.n(j),T=function(e){function t(t){return e.call(this,t)||this}return Object(n.__extends)(t,e),t.prototype.render=function(){return P.a.createElement("div",null,"See github for more information about setting up a reproducable test environment.",P.a.createElement("br",null),P.a.createElement("br",null),P.a.createElement("a",{className:"btn btn-inverse",href:"https://github.com/grafana/grafana/tree/master/devenv",target:"_blank",rel:"noopener"},"Github"),P.a.createElement("br",null))},t}(j.PureComponent),q=function(e){function t(){return null!==e&&e.apply(this,arguments)||this}return Object(n.__extends)(t,e),t.prototype.render=function(){return P.a.createElement("div",null)},t}(j.PureComponent);r.d(t,"plugin",function(){return F});var D=function(){function e(){}return e.template="<h2>Annotation scenario</h2>",e}(),F=new a.DataSourcePlugin(b).setConfigEditor(q).setQueryCtrl(O).setAnnotationQueryCtrl(D).addConfigPage({title:"Setup",icon:"fa fa-list-alt",body:T,id:"setup"})}}]);
//# sourceMappingURL=testDataDSPlugin.fabf58cbd84a6ac3523b.js.map