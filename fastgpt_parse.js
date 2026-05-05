function decodeXmlEntities(str) {
    const entities = {
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&apos;': "'"
    };

    return str.replace(/&(lt|gt|amp|quot|apos);/g, (match) => entities[match]);
}

function extractXmlTag(xml, tagName) {
    let reg = new RegExp(`<${tagName}>([\\s\\S]*?)<\\/${tagName}>`, 'g');
    let lastMatch = null;
    let match = null;

    while ((match = reg.exec(xml)) !== null) {
        lastMatch = match;
    }

    return lastMatch ? decodeXmlEntities(lastMatch[1].trim()) : null;
}

function main({ s }) {
    let success = parseInt(extractXmlTag(s, "success"));
    let reason = "";
    let sql = "";
    let sqlTime = "";
    if (success > 0) {
        sql = extractXmlTag(s, "sql");
        sqlTime = extractXmlTag(s, "sql_time");
    } else {
        reason = extractXmlTag(s, "reason");
    }
    return { success, reason, sql, sqlTime };
}
