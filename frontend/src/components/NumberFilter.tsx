import { useId, useState } from 'react';
import type { FormEvent } from 'react';
import { formatCount, parseBoundedInteger } from '../format';

interface NumberFilterProps {
  label: string;
  bounds: { min: number; max: number; initial: number };
  onApply: (value: number) => void;
}

export function NumberFilter({ label, bounds, onApply }: NumberFilterProps) {
  const id = useId();
  const [draft, setDraft] = useState(String(bounds.initial));
  const [invalid, setInvalid] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = parseBoundedInteger(draft, bounds.min, bounds.max);
    setInvalid(value === null);
    if (value !== null) onApply(value);
  }

  return (
    <form className="number-filter" onSubmit={submit} noValidate>
      <label htmlFor={id}>{label}</label>
      <div className="filter-controls">
        <input id={id} inputMode="numeric" type="number" min={bounds.min} max={bounds.max} step={1}
          value={draft} aria-invalid={invalid} aria-describedby={invalid ? `${id}-error` : undefined}
          onChange={event => { setDraft(event.target.value); setInvalid(false); }} />
        <button className="button button-small" type="submit">Apply</button>
      </div>
      {invalid && <span id={`${id}-error`} className="filter-error" role="alert">
        Enter a whole number from {formatCount(bounds.min)} to {formatCount(bounds.max)}.
      </span>}
    </form>
  );
}
