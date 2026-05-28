const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const ARTICLES_DIR = path.join(__dirname, "..", "articles");

function countWords(text) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function processArticle(filePath) {
  const html = fs.readFileSync(filePath, "utf-8");
  const dom = new JSDOM(html);
  const doc = dom.window.document;

  const content = doc.querySelector(".article-content");
  if (!content) {
    console.log(`  ⚠ No .article-content in ${path.basename(filePath)}, skipping`);
    return;
  }

  // Clone so we can strip non-prose elements before counting
  const clone = content.cloneNode(true);

  // Remove things that aren't article prose
  clone.querySelectorAll(
    ".scrolly-graphic, .scrolly-spacer, .course-explorer, svg, script, style, .es-table, .es-chart, .sg-calc, .sg-diagram"
  ).forEach(el => el.remove());

  const wordCount = countWords(clone.textContent);

  // Update the meta line — preserve the date/author, swap the word count
  const metaLine = doc.querySelector(".article-meta-line");
  if (metaLine) {
    // Expecting format: "XXX words · June 2026 · Rosie Kipling"
    const parts = metaLine.textContent.split("·").map(s => s.trim());
    parts[0] = `${wordCount} words`;
    metaLine.textContent = parts.join(" · ");

    fs.writeFileSync(filePath, dom.serialize(), "utf-8");
    console.log(`  ✓ ${path.basename(filePath)}: ${wordCount} words`);
  } else {
    console.log(`  ⚠ No .article-meta-line in ${path.basename(filePath)}`);
  }
}

const files = fs.readdirSync(ARTICLES_DIR)
  .filter(f => f.endsWith(".html") && !f.startsWith("_"))
  .map(f => path.join(ARTICLES_DIR, f));

console.log(`Updating word counts for ${files.length} articles...`);
files.forEach(processArticle);
console.log("Done.");