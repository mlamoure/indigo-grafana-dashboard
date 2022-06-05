import { variableAdapters } from 'app/features/variables/adapters';
import { hasOptions } from 'app/features/variables/guard';
import { VariableModel } from 'app/features/variables/types';

import { Report } from '../../types';

/**
 * Convert variable values to CSV and remove all empty keys before sending to backend
 * @param variables
 */
export const variablesToCsv = (variables?: VariableModel[]) => {
  if (!variables?.length) {
    return {};
  }

  return Object.fromEntries(
    variables.map((variable) => {
      const { getValueForUrl } = variableAdapters.get(variable.type);
      const value = getValueForUrl(variable);
      return [variable.name, Array.isArray(value) ? value.join(',') : value];
    })
  );
};

export const applyDefaultVariables = (variables: VariableModel[], reportVariables?: Report['templateVars']) => {
  if (!reportVariables || !Object.keys(reportVariables).length) {
    return variables;
  }

  return variables.map((variable) => {
    const reportVariable = reportVariables[variable.name];
    if (!reportVariable || !hasOptions(variable)) {
      return variable;
    }

    const split = reportVariable.split(',');
    const values = split
      .map((str) => variable.options.find((opt) => opt.value === str) || { text: str, value: str })
      .filter(Boolean);

    return {
      ...variable,
      current: { ...variable.current, text: values.map((val) => val?.text), value: values.map((val) => val?.value) },
      options: variable.options.map((option) => ({
        ...option,
        selected: typeof option.value === 'string' && split.includes(option.value),
      })),
    };
  });
};

export const collectVariables = () => {
  const variablePrefix = 'var-';
  const urlParams = new URLSearchParams(window.location.search);
  const variables: Record<string, string[]> = {};

  for (const [key, value] of urlParams.entries()) {
    if (key.startsWith(variablePrefix)) {
      const newKey = key.replace(variablePrefix, '');
      variables[newKey] = [...(variables[newKey] || []), value];
    }
  }

  return Object.fromEntries(Object.entries(variables).map(([key, value]) => [key, value.join(',')]));
};
