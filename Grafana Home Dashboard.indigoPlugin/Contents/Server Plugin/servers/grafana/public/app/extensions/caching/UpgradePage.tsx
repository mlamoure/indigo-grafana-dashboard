import React, { useEffect } from 'react';

import Page from 'app/core/components/Page/Page';
import { UpgradeBox } from 'app/core/components/Upgrade/UpgradeBox';

import { connector, DataSourceCacheUpgradeContent, Props } from './DataSourceCache';

export const DataSourceUpgradePage = ({ navModel, pageId, loadDataSource, loadDataSourceMeta }: Props) => {
  useEffect(() => {
    loadDataSource(pageId).then(loadDataSourceMeta);
  }, [pageId, loadDataSourceMeta, loadDataSource]);

  return (
    <Page navModel={navModel}>
      <Page.Contents>
        <UpgradeBox featureName={'query caching'} featureId={'query-caching'} />
        <DataSourceCacheUpgradeContent />
      </Page.Contents>
    </Page>
  );
};

export default connector(DataSourceUpgradePage);
