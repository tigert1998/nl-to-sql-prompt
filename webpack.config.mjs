import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default {
    mode: 'production',
    entry: './fastgpt-parse.mjs',
    output: {
        filename: 'fastgpt-parse.bundle.js',
        path: path.resolve(__dirname, 'dist'),
        library: '__app__',
        libraryTarget: 'var',
    },
    optimization: {
        minimize: true
    },
};