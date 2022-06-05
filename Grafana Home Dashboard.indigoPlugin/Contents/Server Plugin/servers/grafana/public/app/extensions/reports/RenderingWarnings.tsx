import React from 'react';

import { Alert } from '@grafana/ui';

export interface Props {
  variant?: 'info' | 'error';
}

const actionMessage = 'Please contact your Grafana administrator to install the plugin.';

const NoRendererInfoMessage = (): JSX.Element => {
  return (
    <>
      <>To generate PDF reports, you must install the </>
      <a
        href="https://grafana.com/grafana/plugins/grafana-image-renderer"
        target="_blank"
        rel="noopener noreferrer"
        className="external-link"
      >
        Grafana Image Renderer
      </a>
      <> plugin.</>
    </>
  );
};

export const NoRendererInfoBox = ({ variant = 'info' }: Props): JSX.Element => {
  return (
    <Alert title="Image renderer plugin not installed" severity={variant}>
      <NoRendererInfoMessage /> <br />
      {actionMessage}
    </Alert>
  );
};

const OldRendererInfoMessage = (): JSX.Element => {
  return (
    <>
      <>To generate CSV files, you must update the </>
      <a
        href="https://grafana.com/grafana/plugins/grafana-image-renderer"
        target="_blank"
        rel="noopener noreferrer"
        className="external-link"
      >
        Grafana Image Renderer
      </a>
      <> plugin.</>
    </>
  );
};

export const OldRendererInfoBox = (): JSX.Element => {
  return (
    <Alert title="You are using an old version of the image renderer plugin" severity="warning">
      <OldRendererInfoMessage /> <br />
      {actionMessage}
    </Alert>
  );
};
