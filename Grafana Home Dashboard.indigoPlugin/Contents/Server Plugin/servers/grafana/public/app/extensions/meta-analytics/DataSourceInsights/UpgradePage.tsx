import React, { useEffect } from 'react';

import { useTheme2 } from '@grafana/ui';
import Page from 'app/core/components/Page/Page';
import { UpgradeBox, UpgradeContent } from 'app/core/components/Upgrade/UpgradeBox';

import { connector, Props } from './DataSourceInsights';

export const DataSourceUpgradePage = ({
  navModel,
  dataSourceUid,
  loadDataSource,
  loadDataSourceMeta,
}: Omit<Props, 'theme'>) => {
  const theme = useTheme2();

  useEffect(() => {
    loadDataSource(dataSourceUid).then(loadDataSourceMeta);
  }, [dataSourceUid, loadDataSource, loadDataSourceMeta]);

  return (
    <Page navModel={navModel}>
      <Page.Contents>
        <UpgradeBox featureName={'data source usage insights'} featureId={'data-source-insights'} />
        <UpgradeContent
          listItems={[
            'Demonstrate and improve the value of your observability service by keeping track of user engagement',
            'Keep Grafana performant by identifying and fixing slow, error-prone data sources',
            'Clean up your instance by finding and removing unused data sources',
            'Review individual data source usage insights at a glance in the UI, sort search results by usage and errors, or dig into detailed usage logs',
          ]}
          image={`datasource-insights-${theme.isLight ? 'light' : 'dark'}.png`}
          featureName={'data source usage insights'}
          description={
            'Usage Insights provide detailed information about data source usage, like the number of views, queries, and errors users have experienced. You can use this to improve users’ experience and troubleshoot issues'
          }
          featureUrl={'https://grafana.com/docs/grafana/latest/enterprise/usage-insights/dashboard-datasource-insights'}
        />
      </Page.Contents>
    </Page>
  );
};

export default connector(DataSourceUpgradePage);
