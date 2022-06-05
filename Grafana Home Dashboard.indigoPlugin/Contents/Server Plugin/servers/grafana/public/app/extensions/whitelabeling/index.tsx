import { css, cx } from '@emotion/css';
import React from 'react';

import { config } from '@grafana/runtime';
import { styleMixins } from '@grafana/ui';
import { Branding, BrandComponentProps } from 'app/core/components/Branding/Branding';
import { setFooterLinksFn, FooterLink } from 'app/core/components/Footer/Footer';

interface WhitelabelingSettings {
  links: FooterLink[];
  appTitle: string;
  loginSubtitle: string;
  loginTitle: string;
  loginLogo: string;
  loginBackground: string;
  loginBoxBackground: string;
  menuLogo: string;
}

export function initWhitelabeling() {
  const settings = (config as any).whitelabeling as WhitelabelingSettings;
  if (!settings) {
    return;
  }

  Branding.LoginTitle = 'Welcome to Grafana Enterprise';

  if (settings.links.length > 0) {
    setFooterLinksFn(() => {
      return settings.links.map((link) => ({ ...link, target: '_blank' }));
    });
  }

  if (settings.appTitle) {
    Branding.AppTitle = settings.appTitle;
  }

  if (settings.loginLogo) {
    Branding.LoginLogo = (props: BrandComponentProps) => (
      <img
        className={cx(
          props.className,
          css`
            max-width: 150px;

            @media ${styleMixins.mediaUp(config.theme.breakpoints.sm)} {
              max-width: 250px;
            }
          `
        )}
        src={settings.loginLogo}
      />
    );
    Branding.LoginLogo.displayName = 'BrandingLoginLogo';

    // Reset these to not break existing login screens
    Branding.LoginTitle = '';
    Branding.GetLoginSubTitle = () => '';
  }

  if (settings.loginTitle) {
    Branding.LoginTitle = settings.loginTitle;
  }

  if (settings.loginSubtitle) {
    Branding.GetLoginSubTitle = () => settings.loginSubtitle;
  }

  if (settings.menuLogo) {
    Branding.MenuLogo = (props: BrandComponentProps) => <img className={props.className} src={settings.menuLogo} />;
    Branding.MenuLogo.displayName = 'BrandingMenuLogo';
  }

  if (settings.loginBackground) {
    const background = css`
      background: ${settings.loginBackground};
      background-size: cover;
    `;

    Branding.LoginBackground = (props: BrandComponentProps) => (
      <div className={cx(background, props.className)}>{props.children}</div>
    );
    Branding.LoginBackground.displayName = 'BrandingLoginBackground';
  }

  if (settings.loginBoxBackground) {
    const background = css`
      background: ${settings.loginBoxBackground};
      background-size: cover;
    `;

    Branding.LoginBoxBackground = () => background;
  }
}
