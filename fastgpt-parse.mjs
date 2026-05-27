import { load } from 'js-yaml';

let main = ({ s }) => {
    const regex = /```ya?ml\s([\s\S]*?)\s```/g;
    let matches = [];
    let match;

    while ((match = regex.exec(s)) !== null) {
        matches.push(match[1]);
    }

    if (matches.length === 0) {
        return null;
    }

    const lastBlockContent = matches.at(-1).trim();

    try {
        return load(lastBlockContent);
    } catch (error) {
        return null;
    }
}

globalThis.main = main;
