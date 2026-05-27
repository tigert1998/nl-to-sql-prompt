const path = require('path');

module.exports = {
    mode: 'production',
    entry: './fastgpt-parse.js',
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