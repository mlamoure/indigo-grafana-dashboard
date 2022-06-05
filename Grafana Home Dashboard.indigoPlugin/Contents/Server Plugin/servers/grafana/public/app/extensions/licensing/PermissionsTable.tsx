import { css } from '@emotion/css';
import { orderBy } from 'lodash';
import React, { useEffect, useMemo, useState } from 'react';

import { GrafanaTheme2, SelectableValue } from '@grafana/data';
import { Field, Icon, LinkButton, Pagination, RadioButtonGroup, Select, useStyles2 } from '@grafana/ui';
import { Loader } from 'app/features/plugins/admin/components/Loader';

import { getPermissionsReport } from './state/api';
import { PermissionsReport } from './types';

import { initLicenseWarnings } from './index';

const resourceFilterOptions: Array<SelectableValue<string>> = [
  { label: 'All', value: 'all' },
  { label: 'Dashboards', value: 'dashboard' },
  { label: 'Folders', value: 'folder' },
];

const permissionOptions = [
  { value: 'all', label: 'All' },
  { value: 'admin', label: 'Admin' },
  { value: 'editor', label: 'Editor' },
];

const PAGE_SIZE = 10;

const filterRecords = (records: PermissionsReport[] | null, resourceFilter = 'all', permissionFilter = 'all') => {
  if (!records?.length || (resourceFilter === 'all' && permissionFilter === 'all')) {
    return records;
  }
  let filteredRecords = records;

  if (resourceFilter !== 'all') {
    filteredRecords = filteredRecords.filter((record) =>
      resourceFilter === 'folder' ? record.isFolder : !record.isFolder
    );
  }

  if (permissionFilter !== 'all') {
    filteredRecords = filteredRecords.filter((record) => record.customPermissions.toLowerCase() === permissionFilter);
  }

  return filteredRecords;
};

type Order = {
  field: string;
  direction: 'asc' | 'desc';
};

const orderRecords = (records: PermissionsReport[] | null, { field, direction }: Order) => {
  if (!field || !records) {
    return records;
  }

  return orderBy(records, (record) => String(record[field as keyof PermissionsReport]).toLowerCase(), direction);
};

export interface Props {
  reportUrl: string;
}

const headerFields: Array<{ label: string; value: keyof PermissionsReport }> = [
  { label: 'Ord ID', value: 'orgId' },
  { label: 'Type', value: 'isFolder' },
  { label: 'Resource title (URL)', value: 'title' },
  { label: 'Grantee type', value: 'granteeType' },
  { label: 'Grantee name', value: 'granteeName' },
  { label: 'Custom permission', value: 'customPermissions' },
  { label: 'Org role', value: 'orgRole' },
  { label: 'Users affected', value: 'usersCount' },
];

export const PermissionsTable = ({ reportUrl }: Props) => {
  const [permissionsRecords, setPermissionsRecords] = useState<PermissionsReport[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [resourceFilter, setResourceFilter] = useState<string>('all');
  const [permissionFilter, setPermissionFilter] = useState<SelectableValue<string>>({ value: 'all', label: 'All' });
  const [order, setOrder] = useState<Order>({ field: '', direction: 'desc' });
  const styles = useStyles2(getStyles);

  const filteredRecords = useMemo(
    () => filterRecords(permissionsRecords, resourceFilter, permissionFilter.value),
    [permissionsRecords, resourceFilter, permissionFilter.value]
  );

  useEffect(() => {
    const getData = async () => {
      const records = await getPermissionsReport().catch(() => null);
      setPermissionsRecords(records);
      setIsLoading(false);
    };
    getData();

    return initLicenseWarnings;
  }, []);

  // Reset currentPage whenever any filter is changed
  useEffect(() => {
    setCurrentPage(1);
  }, [permissionFilter.value, resourceFilter]);

  const orderField = (field: string) => {
    let direction: Order['direction'] = 'desc';
    if (field === order.field) {
      if (order.direction === 'desc') {
        direction = 'asc';
      } else {
        direction = 'desc';
      }
    }

    setOrder({ field, direction });
  };

  if (isLoading) {
    return <Loader text={'Loading permissions data...'} />;
  }

  if (!permissionsRecords) {
    return <p>No permission is currently set.</p>;
  }

  return (
    <>
      <div className={styles.filterRow}>
        <div className={styles.filterRow}>
          <Field label={'Resource type'} className={styles.resourceFilter}>
            <RadioButtonGroup options={resourceFilterOptions} value={resourceFilter} onChange={setResourceFilter} />
          </Field>
          <Field label={'Custom permission'}>
            <Select
              value={permissionFilter}
              options={permissionOptions}
              onChange={setPermissionFilter}
              prefix={<Icon name={'filter'} />}
              width={25}
              menuShouldPortal
            />
          </Field>
        </div>

        <Field label={' '}>
          <LinkButton
            variant="secondary"
            href={reportUrl}
            target="_blank"
            rel="noreferrer noopener"
            aria-label="Download dashboard-permissions report"
          >
            Download report as CSV
          </LinkButton>
        </Field>
      </div>
      <table className={styles.table}>
        <thead>
          <tr className={styles.header}>
            {headerFields.map(({ label, value }) => (
              <th key={value} onClick={() => orderField(value)}>
                {label}{' '}
                {order.field === value && <Icon name={order.direction === 'desc' ? 'angle-up' : 'angle-down'} />}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {orderRecords(filteredRecords, order)
            ?.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)
            .map((record) => {
              return (
                <tr key={record.id} className={styles.row}>
                  <td>{record.orgId}</td>
                  <td>{record.isFolder ? 'Folder' : 'Dashboard'}</td>
                  <td>
                    <a
                      href={record.url + (record.isFolder ? '/permissions' : '?editview=permissions')}
                      className={styles.link}
                    >
                      {record.title}
                    </a>
                  </td>
                  <td>{record.granteeType}</td>
                  <td>
                    {record.granteeUrl ? (
                      <a href={record.granteeUrl} className={styles.link}>
                        {record.granteeName}
                      </a>
                    ) : (
                      record.granteeName
                    )}
                  </td>
                  <td>{record.customPermissions}</td>
                  <td>{record.orgRole}</td>
                  <td>{record.usersCount}</td>
                </tr>
              );
            })}
        </tbody>
      </table>
      {filteredRecords!.length > PAGE_SIZE && (
        <div className={styles.pagination}>
          <Pagination
            currentPage={currentPage}
            numberOfPages={Math.ceil(filteredRecords!.length / PAGE_SIZE)}
            onNavigate={(page) => setCurrentPage(page)}
          />
        </div>
      )}
    </>
  );
};

const getStyles = (theme: GrafanaTheme2) => {
  return {
    table: css`
      width: 100%;
    `,
    link: css`
      text-decoration: underline;
    `,
    header: css`
      background-color: ${theme.colors.background.secondary};

      th {
        padding: ${theme.spacing(1)};
        cursor: pointer;

        &:nth-of-type(3) {
          width: 30%;
        }
      }
    `,
    row: css`
      td {
        padding: ${theme.spacing(1)};

        &:nth-of-type(3) {
          width: 30%;
        }
      }

      &:nth-of-type(even) {
        background-color: ${theme.colors.background.secondary};
      }
    `,
    pagination: css`
      display: flex;
      justify-content: center;
      margin: ${theme.spacing(3)} auto 0 auto;

      & > div {
        float: none;
      }
    `,
    filterRow: css`
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: ${theme.spacing(1)};
    `,
    resourceFilter: css`
      margin-right: ${theme.spacing(3)};
    `,
  };
};
