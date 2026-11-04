const fs = require("fs");
const path = require("path");
const postcss = require("postcss");
const tailwindcss = require("tailwindcss");
const autoprefixer = require("autoprefixer");

async function main() {
  const css = fs.readFileSync("app/globals.css", "utf8");
  const result = await postcss([tailwindcss, autoprefixer]).process(css, {
    from: "app/globals.css",
  });
  const dir = path.join("public");
  fs.mkdirSync(dir, { recursive: true });
  const phonwaLanding = fs.readFileSync(path.join("styles", "phonwa-landing.css"), "utf8");
  fs.writeFileSync(path.join(dir, "styles.css"), `${result.css}\n\n/* phonwa landing (design system) */\n${phonwaLanding}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
