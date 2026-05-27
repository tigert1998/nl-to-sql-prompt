function main({ s }) {
    const regex = /```json\s([\s\S]*?)\s```/g;
    let matches = [];
    let match;

    while ((match = regex.exec(text)) !== null) {
        matches.push(match[1]);
    }

    if (matches.length === 0) {
        return null;
    }

    const lastBlockContent = matches.at(-1).trim();

    try {
        return JSON.parse(lastBlockContent);
    } catch (error) {
        return null;
    }
}
