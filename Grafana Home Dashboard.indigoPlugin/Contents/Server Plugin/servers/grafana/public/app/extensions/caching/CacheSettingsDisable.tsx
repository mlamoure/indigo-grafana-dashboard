import React from 'react';

import { Button } from '@grafana/ui';

import { Props } from './DataSourceCache';

export const CacheSettingsDisable = (props: Props) => {
  const { disableDataSourceCache, pageId } = props;
  return (
    <Button variant="destructive" onClick={() => disableDataSourceCache(pageId)}>
      Disable
    </Button>
  );
};
