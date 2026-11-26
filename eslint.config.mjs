// ESLint 10 uses the nearest flat config for each file. The frontend has its own.
// Outside that package, ignore workspace files such as local browser scripts.
export default [{ ignores: ['**/*'] }];
