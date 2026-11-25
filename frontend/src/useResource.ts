import { useEffect, useState } from 'react';
import { ApiError } from './api';

export type Resource<T> = { status: 'loading' } | { status: 'ready'; data: T } | {
  status: 'error'; error: ApiError;
};

export function useResource<T>(load: (signal: AbortSignal) => Promise<T>, revision: number): Resource<T> {
  const [state, setState] = useState<Resource<T>>({ status: 'loading' });

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: 'loading' });
    load(controller.signal).then(
      data => {
        if (!controller.signal.aborted) setState({ status: 'ready', data });
      },
      error => {
        if (!controller.signal.aborted) {
          setState({
            status: 'error',
            error: error instanceof ApiError ? error : new ApiError('Unable to load data. Try reloading.', 'response'),
          });
        }
      },
    );
    return () => controller.abort();
  }, [load, revision]);

  return state;
}
