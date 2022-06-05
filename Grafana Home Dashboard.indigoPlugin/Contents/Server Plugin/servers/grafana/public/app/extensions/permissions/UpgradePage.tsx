import React, { useEffect } from 'react';

import { useTheme2 } from '@grafana/ui';
import Page from 'app/core/components/Page/Page';
import { UpgradeBox, UpgradeContent, UpgradeContentProps } from 'app/core/components/Upgrade/UpgradeBox';

import { connector, Props } from './AccessControlDataSourcePermissions';

export const UpgradePage = ({ navModel, loadDataSource, loadDataSourceMeta, resourceId }: Props) => {
  useEffect(() => {
    loadDataSource(resourceId as any).then(loadDataSourceMeta);
  }, [resourceId, loadDataSource, loadDataSourceMeta]);

  return (
    <Page navModel={navModel}>
      <Page.Contents>
        <UpgradeBox featureName={'data source permissions'} featureId={'data-source-permissions'} />
        <PermissionsUpgradeContent />
      </Page.Contents>
    </Page>
  );
};

export interface PermissionsUpgradeContentProps {
  action?: UpgradeContentProps['action'];
}

export const PermissionsUpgradeContent = ({ action }: PermissionsUpgradeContentProps) => {
  const theme = useTheme2();

  return (
    <UpgradeContent
      action={action}
      featureName={'data source permissions'}
      description={
        'With data source permissions, you can protect sensitive data by limiting access to this data source to specific users, teams, and roles.'
      }
      listItems={[
        'Protect sensitive data, like security logs, production databases, and personally-identifiable information',
        'Clean up users’ experience by hiding data sources they don’t need to use',
        'Share Grafana access more freely, knowing that users will not unwittingly see sensitive data',
      ]}
      image={`ds-permissions-${theme.isLight ? 'light' : 'dark'}.png`}
      featureUrl={'https://grafana.com/docs/grafana/latest/enterprise/datasource_permissions'}
    />
  );
};

export default connector(UpgradePage);
