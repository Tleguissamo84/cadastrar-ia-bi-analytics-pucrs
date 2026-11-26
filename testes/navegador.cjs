(function navegador() {
  "use strict";
  const assert = require("node:assert/strict");
  const fs = require("node:fs/promises");
  const http = require("node:http");
  const os = require("node:os");
  const path = require("node:path");
  const { pathToFileURL } = require("node:url");
  const { chromium } = require(process.env.PLAYWRIGHT_PATH || "playwright");

  async function validar() {
    const temp = await fs.mkdtemp(path.join(os.tmpdir(), "painel-agregado-"));
    const arquivo = path.join(temp, "index.html");
    await fs.copyFile(path.join(__dirname, "../docs/index.html"), arquivo);
    const html = await fs.readFile(arquivo);
    const caminho = "/projeto-exemplo/";
    const server = http.createServer((req, res) => {
      if (req.url === caminho || req.url === `${caminho}index.html`) {
        res.writeHead(200, { "content-type": "text/html; charset=utf-8" }).end(html);
      } else res.writeHead(404).end();
    });
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(0, "127.0.0.1", resolve);
    });
    const url = `http://127.0.0.1:${server.address().port}${caminho}`;
    let browser;
    try {
      browser = await chromium.launch({headless: true, executablePath: process.env.BROWSER_PATH || undefined});
      const context = await browser.newContext({viewport: {width: 1400, height: 900}});
      const rede = [], erros = [];
      await context.route(/^https?:/, route => {
        const pedido = route.request().url();
        if (pedido === url) return route.continue();
        rede.push(pedido);
        return route.abort();
      });
      const page = await context.newPage();
      page.setDefaultTimeout(7000);
      page.on("pageerror", erro => erros.push(erro.message));
      await page.goto(pathToFileURL(arquivo).href);
      assert.equal(await page.locator("h1").innerText(), "Qualidade documental");
      assert.deepEqual(await page.locator(".card-number").allTextContents(), ["10", "190", "190", "19"]);
      assert.deepEqual(await page.locator(".ganho").allTextContents(), ["+100 p.p.", "+90 p.p."]);
      await page.goto(url);
      const entrar = async rota => {
        await page.locator(`nav [data-rota="${rota}"]`).press("Enter");
        await page.locator(`nav [data-rota="${rota}"][aria-current="page"]`).waitFor();
      };
      await entrar("indicadores");
      assert.match(await page.locator("main").innerText(), /10 avaliáveis de 90 testes aplicáveis/);
      assert.match(await page.locator("main").innerText(), /28\/29 valores/);
      const global = page.getByRole("row").filter({hasText:/^Global/});
      assert.doesNotMatch(await global.innerText(), /\d+%/);
      await entrar("pendencias");
      assert.equal(await page.getByRole("table", {name:"Pendências agregadas"}).locator("tbody tr").count(), 3);
      await entrar("metodo");
      assert.match(await page.locator("main").innerText(), /galeria.*acervo restrito/);
      assert.equal(await page.locator("main img").count(), 0);
      await entrar("cores");
      assert.deepEqual(await page.locator(".card-number").allTextContents(), ["10", "7", "3"]);
      await entrar("previsao");
      assert.match(await page.getByRole("table", {name:"Métricas do teste final"}).innerText(), /22\.718,13/);
      for (const figura of await page.locator(".forecast-plot").all()) {
        await page.waitForFunction(img => img.complete && img.naturalWidth > 0, await figura.elementHandle());
      }
      assert.equal(await page.locator(".forecast-plot").count(), 3);
      await page.getByText("Ver valores semana a semana", {exact:true}).press("Enter");
      assert.equal(await page.getByRole("table", {name:"Observado e previsto por semana"}).locator("tbody tr").count(), 13);
      await page.setViewportSize({width: 390, height: 844});
      for (const rota of ["visao-geral", "indicadores", "pendencias", "metodo", "cores", "previsao"]) {
        await entrar(rota);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, rota);
      }
      if (process.env.PAINEL_NOTEBOOK_HTML) {
        await page.goto(pathToFileURL(process.env.PAINEL_NOTEBOOK_HTML).href);
        const frame = page.frameLocator("iframe");
        await frame.locator('nav [data-rota="previsao"]').press("Enter");
        await frame.getByRole("table", {name:"Métricas do teste final"}).waitFor();
        assert.equal(await frame.locator(".forecast-plot").count(), 3);
        console.log("Notebook executado e verificado no iframe.");
      }
      assert.deepEqual(erros, []);
      assert.deepEqual(rede, []);
      console.log("6 seções aprovadas em arquivo isolado e hospedagem local em subcaminho, sem requisições externas.");
    } finally {
      if (browser) await browser.close();
      await new Promise(resolve => server.close(resolve));
      await fs.unlink(arquivo);
      await fs.rmdir(temp);
    }
  }

  validar().catch(error => { console.error(error.message); process.exitCode = 1; });
})();

