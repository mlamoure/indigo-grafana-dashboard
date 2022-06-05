import React, { useEffect } from 'react';
import { connect, ConnectedProps } from 'react-redux';

import { Permissions } from 'app/core/components/AccessControl';
import Page from 'app/core/components/Page/Page';
import { UpgradeBox } from 'app/core/components/Upgrade/UpgradeBox';
import { contextSrv } from 'app/core/core';
import { GrafanaRouteComponentProps } from 'app/core/navigation/types';
import { getNavModel } from 'app/core/selectors/navModel';
import { highlightTrial } from 'app/features/admin/utils';
import { loadDataSource, loadDataSourceMeta } from 'app/features/datasources/state/actions';
import { getDataSourceLoadingNav } from 'app/features/datasources/state/navModel';
import { AccessControlAction } from 'app/types';

import { AccessControlAction as EnterpriseActions, EnterpriseStoreState } from '../types';

interface RouteProps extends GrafanaRouteComponentProps<{ uid: string }> {}

function mapStateToProps(state: EnterpriseStoreState, props: RouteProps) {
  const uid = props.match.params.uid;
  return {
    resourceId: uid,
    navModel: getNavModel(state.navIndex, `datasource-permissions-${uid}`, getDataSourceLoadingNav('permissions')),
  };
}

const mapDispatchToProps = {
  loadDataSource,
  loadDataSourceMeta,
};

export const connector = connect(mapStateToProps, mapDispatchToProps);
export type Props = ConnectedProps<typeof connector>;

const DataSourcePermissions = ({ resourceId, loadDataSource, navModel, loadDataSourceMeta }: Props) => {
  useEffect(() => {
    loadDataSource(resourceId);
  }, [resourceId, loadDataSource]);
  const canListUsers = contextSrv.hasPermission(AccessControlAction.OrgUsersRead);
  const canSetPermissions = contextSrv.hasPermission(EnterpriseActions.DataSourcesPermissionsWrite);

  useEffect(() => {
    // Initialize DS metadata on page load to populate tab navigation
    loadDataSource(resourceId as any).then(loadDataSourceMeta);
  }, [loadDataSource, loadDataSourceMeta, resourceId]);

  return (
    <Page navModel={navModel}>
      <Page.Contents>
        {highlightTrial() && (
          <UpgradeBox
            featureId={'data-source-permissions'}
            eventVariant={'trial'}
            featureName={'data source permissions'}
            text={'Enable data source permissions for free during your trial of Grafana Pro.'}
          />
        )}
        <Permissions
          resource="datasources"
          resourceId={resourceId}
          canListUsers={canListUsers}
          canSetPermissions={canSetPermissions}
        />
      </Page.Contents>
    </Page>
  );
};

export default connector(DataSourcePermissions);
