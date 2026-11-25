import type { ReactNode } from 'react';
import type { Resource } from '../useResource';

interface ResultStateProps<T> {
  resource: Resource<T>;
  title: string;
  children: (data: T) => ReactNode;
}

export function ResultState<T>({ resource, title, children }: ResultStateProps<T>) {
  if (resource.status === 'error') {
    return <p className="panel-message error-message" role="status">{resource.error.message}</p>;
  }
  if (resource.status === 'loading') {
    return <div className="panel-message loading-message" role="status">
      <span className="loading-dot" aria-hidden="true" />Loading {title}…
    </div>;
  }
  return children(resource.data);
}
