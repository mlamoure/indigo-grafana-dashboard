import { css, cx } from '@emotion/css';
import React from 'react';

import { GrafanaTheme } from '@grafana/data';
import { useStyles } from '@grafana/ui';

export interface Props {
  url: string;
  width?: string;
}

export const ImagePreview = ({ url, width = '200px' }: Props) => {
  const styles = useStyles(getStyles);
  return url ? (
    <div
      className={cx(
        styles.wrapper,
        css`
          width: ${width};
        `
      )}
    >
      <img src={url} className={styles.img} />
    </div>
  ) : null;
};

const getStyles = (theme: GrafanaTheme) => {
  return {
    wrapper: css`
      padding: ${theme.spacing.sm};
      border: 1px solid ${theme.colors.border3};
      border-radius: ${theme.border.radius.sm};
      margin-bottom: ${theme.spacing.md};
    `,
    img: css`
      width: 100%;
    `,
  };
};
