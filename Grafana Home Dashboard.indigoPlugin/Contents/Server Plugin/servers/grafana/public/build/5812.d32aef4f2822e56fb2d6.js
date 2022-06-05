"use strict";(self.webpackChunkgrafana=self.webpackChunkgrafana||[]).push([[5812],{"./public/app/features/profile/ChangePasswordPage.tsx":(e,a,s)=>{s.r(a),s.d(a,{ChangePasswordPage:()=>b,default:()=>v});s("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/index.js");var n,r,o=s("./.yarn/__virtual__/react-redux-virtual-7ad20a440e/3/opt/drone/yarncache/react-redux-npm-7.2.6-134f5ed64d-0bf142ce0d.zip/node_modules/react-redux/es/index.js"),t=s("./.yarn/__virtual__/react-use-virtual-00326e70ba/3/opt/drone/yarncache/react-use-npm-17.3.2-a032cbeb01-7379460f51.zip/node_modules/react-use/esm/useMount.js"),i=s("./public/app/core/components/Page/Page.tsx"),c=s("./public/app/core/selectors/navModel.ts"),d=s("./.yarn/__virtual__/@emotion-css-virtual-72c314ddb1/3/opt/drone/yarncache/@emotion-css-npm-11.7.1-25ff8755a7-ac1f56656f.zip/node_modules/@emotion/css/dist/emotion-css.esm.js"),u=s("./packages/grafana-ui/src/index.ts"),l=s("./public/app/core/config.ts"),p=s("./public/app/core/components/PasswordField/PasswordField.tsx"),w=s("../../opt/drone/yarncache/react-npm-17.0.2-99ba37d931-b254cc17ce.zip/node_modules/react/jsx-runtime.js");const h=e=>{var a,s;let{user:o,onChangePassword:t,isSaving:i}=e;const{ldapEnabled:c,authProxyEnabled:h,disableLoginForm:f}=l.ZP,m=(null===(a=o.authLabels)||void 0===a?void 0:a.length)&&o.authLabels[0];return c||h?n||(n=(0,w.jsx)("p",{children:"You cannot change password when LDAP or auth proxy authentication is enabled."})):m&&f?r||(r=(0,w.jsx)("p",{children:"Password cannot be changed here."})):(0,w.jsx)("div",{className:d.css`
        max-width: 400px;
      `,children:(0,w.jsx)(u.Form,{onSubmit:t,children:e=>{var a,n,r;let{register:o,errors:t,getValues:c}=e;return(0,w.jsxs)(w.Fragment,{children:[(0,w.jsx)(u.Field,{label:"Old password",invalid:!!t.oldPassword,error:null==t||null===(a=t.oldPassword)||void 0===a?void 0:a.message,children:(0,w.jsx)(p.Z,Object.assign({id:"current-password",autoComplete:"current-password"},o("oldPassword",{required:"Old password is required"})))}),(0,w.jsx)(u.Field,{label:"New password",invalid:!!t.newPassword,error:null==t||null===(n=t.newPassword)||void 0===n?void 0:n.message,children:(0,w.jsx)(p.Z,Object.assign({id:"new-password",autoComplete:"new-password"},o("newPassword",{required:"New password is required",validate:{confirm:e=>e===c().confirmNew||"Passwords must match",old:e=>e!==c().oldPassword||"New password can't be the same as the old one."}})))}),(0,w.jsx)(u.Field,{label:"Confirm password",invalid:!!t.confirmNew,error:null==t||null===(r=t.confirmNew)||void 0===r?void 0:r.message,children:(0,w.jsx)(p.Z,Object.assign({id:"confirm-new-password",autoComplete:"new-password"},o("confirmNew",{required:"New password confirmation is required",validate:e=>e===c().newPassword||"Passwords must match"})))}),(0,w.jsxs)(u.HorizontalGroup,{children:[s||(s=(0,w.jsx)(u.Button,{variant:"primary",disabled:i,children:"Change Password"})),(0,w.jsx)(u.LinkButton,{variant:"secondary",href:`${l.ZP.appSubUrl}/profile`,fill:"outline",children:"Cancel"})]})]})}})})};var f,m=s("./public/app/features/profile/state/actions.ts");const g={loadUser:m.II,changePassword:m.Cp};function b(e){let{navModel:a,loadUser:s,isUpdating:n,user:r,changePassword:o}=e;return(0,t.Z)((()=>s())),(0,w.jsx)(i.Z,{navModel:a,children:(0,w.jsx)(i.Z.Contents,{isLoading:!Boolean(r),children:r?(0,w.jsxs)(w.Fragment,{children:[f||(f=(0,w.jsx)("h3",{className:"page-heading",children:"Change Your Password"})),(0,w.jsx)(h,{user:r,onChangePassword:o,isSaving:n})]}):null})})}const v=(0,o.connect)((function(e){const a=e.user,{isUpdating:s,user:n}=a;return{navModel:(0,c.h)(e.navIndex,"change-password"),isUpdating:s,user:n}}),g)(b)},"./public/app/features/profile/state/actions.ts":(e,a,s)=>{s.d(a,{Cp:()=>t,II:()=>c,Lj:()=>l,PA:()=>i,cc:()=>d,hz:()=>u});var n=s("./packages/grafana-runtime/src/index.ts"),r=s("./public/app/features/profile/api.ts"),o=s("./public/app/features/profile/state/reducers.ts");function t(e){return async function(a){a((0,o.zc)({updating:!0})),await r.h.changePassword(e),a((0,o.zc)({updating:!1}))}}function i(){return async function(e){await e(c()),e((async function(e){e((0,o.qD)());const a=await r.h.loadTeams();e((0,o.PL)({teams:a}))})),e((async function(e){e((0,o.$S)());const a=await r.h.loadOrgs();e((0,o.Ns)({orgs:a}))})),e((async function(e){e((0,o.Uk)());const a=await r.h.loadSessions();e((0,o.z0)({sessions:a}))}))}}function c(){return async function(e){const a=await r.h.loadUser();e((0,o.aw)({user:a}))}}function d(e){return async function(a){a((0,o.zc)({updating:!0})),await r.h.revokeUserSession(e),a((0,o.p$)({tokenId:e}))}}function u(e){return async function(a){a((0,o.zc)({updating:!0})),await r.h.setUserOrg(e),window.location.href=n.config.appSubUrl+"/profile"}}function l(e){return async function(a){a((0,o.zc)({updating:!0})),await r.h.updateUserProfile(e),await a(c()),a((0,o.zc)({updating:!1}))}}},"./.yarn/__virtual__/react-use-virtual-00326e70ba/3/opt/drone/yarncache/react-use-npm-17.3.2-a032cbeb01-7379460f51.zip/node_modules/react-use/esm/useMount.js":(e,a,s)=>{s.d(a,{Z:()=>r});var n=s("./.yarn/__virtual__/react-use-virtual-00326e70ba/3/opt/drone/yarncache/react-use-npm-17.3.2-a032cbeb01-7379460f51.zip/node_modules/react-use/esm/useEffectOnce.js");const r=function(e){(0,n.Z)((function(){e()}))}}}]);
//# sourceMappingURL=5812.d32aef4f2822e56fb2d6.js.map