"use strict";(self.webpackChunkgrafana=self.webpackChunkgrafana||[]).push([[53],{"./public/app/plugins/panel/icon/module.tsx":(e,t,i)=>{i.r(t),i.d(t,{plugin:()=>u});var n=i("./packages/grafana-data/src/index.ts"),s=i("./public/app/features/canvas/elements/icon.tsx"),a=i("./public/app/plugins/panel/canvas/editor/options.ts"),o=i("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js"),p=i("./public/app/features/canvas/runtime/element.tsx"),d=i("./public/app/features/dimensions/index.ts"),r=i("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");function l(e,t,i){return t in e?Object.defineProperty(e,t,{value:i,enumerable:!0,configurable:!0,writable:!0}):e[t]=i,e}class h extends o.Component{constructor(e){super(e),l(this,"element",void 0),l(this,"initElement",(e=>(this.element=new p.f(s.e,e.options.root),this.updateSize(e),this.element.updateData(this.dims),this.element))),l(this,"updateSize",(e=>{const{width:t,height:i}=e;this.element.anchor={top:!0,left:!0},this.element.placement={left:0,top:0,width:t,height:i},this.element.updateSize(t,i)})),l(this,"dims",{getColor:e=>(0,d.FP)(this.props.data,e),getScale:e=>(0,d.pb)(this.props.data,e),getScalar:e=>(0,d.z2)(this.props.data,e),getText:e=>(0,d.WO)(this.props.data,e),getResource:e=>(0,d.Qz)(this.props.data,e)}),this.element=this.initElement(e)}shouldComponentUpdate(e){var t,i;const{width:n,height:s,data:a}=this.props;let o=!1;return n===e.width&&s===e.height||(this.updateSize(e),o=!0),a!==e.data&&(this.element.updateData(this.dims),o=!0),(null===(t=this.props.options)||void 0===t?void 0:t.root)!==(null===(i=e.options)||void 0===i?void 0:i.root)&&(this.initElement(e),o=!0),o}render(){const{width:e,height:t}=this.props;return(0,r.jsx)("div",{style:{width:e,height:t,overflow:"hidden",position:"relative"},children:this.element.render()})}}const c={root:{config:{path:{mode:d.Q8.Fixed,fixed:"img/icons/unicons/analysis.svg"},fill:{fixed:"green"}}}},u=new n.PanelPlugin(h).setNoPadding().useFieldConfig({standardOptions:{[n.FieldConfigProperty.Mappings]:{settings:{icon:!0}}}}).setPanelOptions((e=>{e.addNestedOptions({category:["Icon"],path:"root",build:(e,t)=>{s.e.registerOptionsUI(e,t),a.I.addBackground(e,t),a.I.addBorder(e,t)},defaultValue:c.root})}))}}]);
//# sourceMappingURL=iconPanel.d32aef4f2822e56fb2d6.js.map