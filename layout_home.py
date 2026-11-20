"""HTML da home nova (template do 006/007/008 adaptado ao financiamento de veículos). Os marcadores @@NOME@@ são trocados por gerador_veiculos.gerar_index.

Sem atributo style nem script inline: a CSP desta página não permite. Barras são SVG com atributos; a lógica fica em src/home.js.
"""

# Logo desenhado à mão (48x48): frasco de laboratório com proporção de verdade (gargalo, ombros, base arredondada), líquido com onda,
# três barras de dados dentro, bolhas subindo pelo gargalo e uma tendência de pontos acima. Traço e preenchimento usam currentColor
# (a cor vem do CSS: azul de veículos no cabeçalho, claro no ícone). Mesmo desenho em logo.svg e favicon.svg (gerados por gerar_icones.py).
LOGO_PATHS = (
    '<path d="M17.4 5.8h13.2" stroke-width="2.2"/>'
    '<path d="M19.6 5.8V19.2L9.3 37.6c-1.3 2.3.4 4.9 3 4.9h23.4c2.6 0 4.3-2.6 3-4.9L28.4 19.2V5.8" stroke-width="2.2"/>'
    '<path d="M13.4 30.6c3.1-2 5.9 1.4 10.6-.1s7.2-1.7 10.9.1l4 7c.9 1.6-.3 3.4-2.1 3.4H11.5c-1.8 0-3-1.8-2.1-3.4z" fill="currentColor" fill-opacity=".2" stroke="none"/>'
    '<path d="M13.2 30.8c3.1-1.8 5.9 1.2 10.8-.2s7.2-1.6 10.9.2" stroke-width="1.5"/>'
    '<g fill="currentColor" stroke="none"><rect x="15.6" y="35.2" width="3.2" height="4.4" rx="1"/><rect x="20.4" y="33.1" width="3.2" height="6.5" rx="1"/>'
    '<rect x="25.2" y="34.2" width="3.2" height="5.4" rx="1"/><rect x="30" y="32" width="3.2" height="7.6" rx="1"/>'
    '<circle cx="24" cy="14.6" r="1.3"/><circle cx="24.9" cy="10.6" r=".9"/><circle cx="23.3" cy="22.3" r="1.6"/>'
    '<circle cx="34.6" cy="9.4" r="1.7"/><circle cx="40.2" cy="4.8" r="1.7"/></g>'
    '<path d="M34.6 9.4l5.6-4.6" stroke-width="1.4"/>'
)

LOGO_SVG = ('<svg viewBox="0 0 48 48" width="@@W@@" height="@@W@@" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            + LOGO_PATHS + '</svg>')

LOGO = '<span class="tile">' + LOGO_SVG.replace("@@W@@", "32") + '</span>'

LAYOUT = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@TITLE@@</title>
<meta name="description" content="@@DESC@@">
<link rel="canonical" href="@@CANONICAL@@">
<link rel="icon" href="/favicon.ico?v=@@ICONV@@" sizes="any">
<link rel="icon" href="/favicon-32.png?v=@@ICONV@@" type="image/png" sizes="32x32">
<link rel="icon" href="/favicon-192.png?v=@@ICONV@@" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="/apple-touch-icon.png?v=@@ICONV@@">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="Datalab Global">
<meta property="og:title" content="@@TITLE@@">
<meta property="og:description" content="@@DESC@@">
<meta property="og:url" content="@@CANONICAL@@">
<meta property="og:image" content="@@DOMINIO@@/og-image.png?v=@@ICONV@@">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="@@TITLE@@">
<meta name="twitter:description" content="@@DESC@@">
<meta name="twitter:image" content="@@DOMINIO@@/og-image.png?v=@@ICONV@@">
<meta name="theme-color" content="#020617">
<link rel="preload" href="/fonts/playfair-display-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/home.css?v=@@CSSV@@">
<link rel="alternate" type="application/atom+xml" title="Taxas de financiamento de veículos" href="/feed.xml">
@@JSONLD@@@@MEDICAO@@</head>
<body>
<a href="#conteudo" class="skip">Ir para o conteúdo</a>
<header class="top">
  <div class="wrap">
    <a href="/" class="brand" aria-label="Datalab Global — Financiamento de veículos, página inicial">@@LOGO@@<span class="wm"><b>Datalab</b><i>GLOBAL</i></span><span class="prod">Veículos</span></a>
    <nav class="m" aria-label="Principal">@@NAV@@</nav>
    <div class="free"><span class="dot"></span>Simulação gratuita</div>
    <details class="menu">
      <summary>Menu</summary>
      <nav aria-label="Menu">@@NAVMOBILE@@</nav>
    </details>
  </div>
</header>

<main id="conteudo" class="wrap">
@@MAIN@@
</main>

<footer class="rod">
  <div class="wrap">
    <div class="cols">
      <div>
        <a href="/" class="brand" aria-label="Datalab Global — Financiamento de veículos">@@LOGO@@<span class="wm"><b>Datalab</b><i>GLOBAL</i></span></a>
        <p>Simulador de financiamento de carro novo, carro usado e moto: parcela, CET e custo total com as taxas do Banco Central, antes de qualquer pedido.</p>
      </div>
      <nav aria-label="Entenda"><h2>Entenda</h2><ul>@@FOOT_ENTENDA@@</ul></nav>
      <nav aria-label="Transparência"><h2>Transparência</h2><ul>@@FOOT_TRANSP@@</ul></nav>
      <nav aria-label="Legal"><h2>Legal</h2><ul>@@FOOT_LEGAL@@</ul></nav>
      <nav aria-label="Outros simuladores da Datalab Global"><h2>Outros simuladores</h2><ul>@@FOOT_OUTROS@@</ul></nav>
    </div>
    <div class="base">
      <p>Taxas atualizadas em @@ATUALIZADO@@ (Banco Central do Brasil, semana de @@PERIODO@@).</p>
      <p>Datalab Global é marca de @@RAZAO@@. Contato: <a href="mailto:contato@datalabglobal.com">contato@datalabglobal.com</a>.</p>
      <p>A simulação é uma estimativa educativa, não é oferta nem proposta de crédito. A taxa final depende da análise do banco, sem garantia de aprovação.</p>
    </div>
  </div>
</footer>
@@SCRIPTS@@</body>
</html>
"""

HOME_MAIN = """  <section class="hero">
    <h1>Simulador de financiamento de <em>veículos</em></h1>
    <p>Veja a parcela, o CET e o custo total de carro novo, carro usado ou moto, com as taxas dos bancos divulgadas pelo Banco Central.</p>
    <div class="fine">Grátis · sem cadastro · estimativa, não proposta</div>
  </section>

  <div class="grid" id="simulador">
    <section class="panel" aria-labelledby="t-cenario">
      <h2 id="t-cenario">Seu cenário</h2>
      <div class="f">
        <div class="lb" id="lb-categoria">Tipo de veículo</div>
        <div class="seg s3" role="radiogroup" aria-labelledby="lb-categoria">
          <input type="radio" name="categoria" id="cat-novo" value="novo" checked><label for="cat-novo">Carro novo</label>
          <input type="radio" name="categoria" id="cat-usado" value="usado"><label for="cat-usado">Carro usado</label>
          <input type="radio" name="categoria" id="cat-moto" value="moto"><label for="cat-moto">Moto</label>
        </div>
      </div>
      <div class="f">
        <label for="campo-valor">Valor do veículo <span id="rot-valor">preço de tabela ou da loja</span></label>
        <div class="inp"><span class="pre">R$</span><input id="campo-valor" type="text" inputmode="numeric" autocomplete="off" value="80.000" class="num"></div>
        <input id="range-valor" type="range" aria-label="Valor do veículo, controle deslizante" min="30000" max="400000" step="5000" value="80000">
        <div class="slabel"><span id="min-valor">R$ 30 mil</span><span id="max-valor">R$ 400 mil</span></div>
      </div>
      <div class="f">
        <label for="campo-entrada">Entrada <span id="rot-entrada">20% do valor</span></label>
        <div class="inp"><span class="pre">R$</span><input id="campo-entrada" type="text" inputmode="numeric" autocomplete="off" value="16.000" class="num"></div>
        <input id="range-entrada" type="range" aria-label="Entrada, controle deslizante" min="16000" max="72000" step="500" value="16000">
        <div class="slabel"><span id="min-entrada">R$ 16 mil</span><span id="max-entrada">R$ 72 mil</span></div>
        <div class="hint warn" id="msg-entrada" hidden></div>
      </div>
      <div class="f">
        <label for="campo-prazo">Prazo <span id="rot-prazo">de 12 a 60 meses</span></label>
        <div class="inp combo" id="combo-prazo">
          <input id="campo-prazo" type="text" inputmode="numeric" autocomplete="off" value="48" class="num" role="combobox" aria-autocomplete="none" aria-expanded="false" aria-controls="lista-prazo" aria-describedby="msg-prazo" aria-label="Prazo em meses: escolha na lista ou digite">
          <em>meses</em>
          <button type="button" class="caret" id="btn-prazo" aria-label="Abrir a lista de prazos" aria-haspopup="listbox" aria-controls="lista-prazo"><svg viewBox="0 0 12 8" width="12" height="8" aria-hidden="true"><path d="M1 1.5l5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
          <ul class="opts" id="lista-prazo" role="listbox" aria-label="Prazos disponíveis" hidden></ul>
        </div>
        <input id="range-prazo" type="range" aria-label="Prazo em meses, controle deslizante" min="12" max="60" step="1" value="48">
        <div class="slabel"><span>12 meses</span><span id="max-prazo">60 meses</span></div>
        <div class="hint warn" id="msg-prazo" hidden></div>
      </div>
      <div class="f">
        <label for="campo-banco">Taxa de referência <span id="rot-banco">média dos bancos</span></label>
        <div class="inp combo" id="combo-banco">
          <input id="campo-banco" type="text" readonly value="Média dos bancos" class="num" role="combobox" aria-autocomplete="none" aria-expanded="false" aria-controls="lista-banco" aria-label="Taxa de referência: escolha um banco na lista">
          <button type="button" class="caret" id="btn-banco" aria-label="Abrir a lista de bancos" aria-haspopup="listbox" aria-controls="lista-banco"><svg viewBox="0 0 12 8" width="12" height="8" aria-hidden="true"><path d="M1 1.5l5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
          <ul class="opts" id="lista-banco" role="listbox" aria-label="Bancos" hidden></ul>
        </div>
        <div class="hint" id="hint-banco">@@D_HINT_BANCO@@</div>
      </div>
      <details class="outra" id="det-taxa">
        <summary>Já tem uma proposta? Use a taxa dela</summary>
        <div class="oi">
          <label for="campo-taxa-prop">Taxa da proposta <span>% ao mês</span></label>
          <div class="inp"><input id="campo-taxa-prop" type="text" inputmode="decimal" autocomplete="off" placeholder="ex.: 1,89" class="num" aria-describedby="msg-taxa-prop"><em>% a.m.</em></div>
          <div class="hint" id="msg-taxa-prop">Deixe em branco para usar a taxa de referência acima. Vale de 0,3 a 6% ao mês.</div>
        </div>
      </details>
    </section>

    <section class="panel resp" id="resultado" aria-labelledby="t-resultado" aria-live="polite">
      <h2 class="kicker kres" id="t-resultado">Resultado da simulação</h2>
      <div class="res">
        <div>
          <div class="kicker" id="r-kicker">Parcela estimada</div>
          <div class="big num"><span id="r-parcela">@@D_PARCELA@@</span> <small>/mês</small></div>
          <div class="dim" id="r-sub">@@D_SUB@@</div>
          <hr class="sep">
          <div class="dim lab">Total estimado das parcelas</div>
          <div class="mid num" id="r-total">@@D_TOTAL@@</div>
          <div class="dim"><a href="/metodologia">Como calculamos</a></div>
        </div>
        <div class="ctx sis">
          <div class="t">CET estimado</div>
          <div class="v num" id="r-cet">@@D_CET@@</div>
          <div class="hint" id="hint-cet">Custo efetivo total ao ano: juros, IOF, registro do contrato e seguro típicos.</div>
        </div>
      </div>
      <div class="callout"><p id="r-resumo">@@D_RESUMO@@</p></div>
      <div class="rosca">
        <svg viewBox="0 0 120 120" width="120" height="120" role="img" id="rosca-svg" aria-label="Do total das parcelas, @@D_PCT_JUROS@@% é juros">
          <circle cx="60" cy="60" r="46" fill="none" stroke="#e3a96b" stroke-width="14"/>
          <circle id="rosca-cred" cx="60" cy="60" r="46" fill="none" stroke="#0ea5e9" stroke-width="14" stroke-dasharray="@@D_ROSCA_P@@ 289.03" transform="rotate(-90 60 60)"/>
          <text x="60" y="61" text-anchor="middle" class="rc-n" id="rosca-pct">@@D_PCT_JUROS@@%</text>
          <text x="60" y="77" text-anchor="middle" class="rc-t">em juros</text>
        </svg>
        <div class="rc-l">
          <div class="kicker">Para onde vai o total</div>
          <div class="lg"><span><s></s>Valor financiado</span><b class="num" id="rosca-cred-v">@@D_L_CRED@@</b></div>
          <div class="lg"><span><s class="jr"></s>Juros</span><b class="num" id="rosca-juros-v">@@D_L_JUROS@@</b></div>
        </div>
      </div>
      <div class="rodape-res">
        <div class="cta">
          <div><strong>Peça uma análise gratuita</strong><span class="s">Com um parceiro de crédito · sem compromisso</span></div>
          <button type="button" class="btn" id="btn-cta">Consultar opções →</button>
        </div>
        <div class="fine2">Estimativa: a taxa final depende da análise do banco e do seu perfil. <a href="/metodologia">Veja como calculamos</a>.</div>
        <div class="copiar"><button type="button" id="btn-copiar">Copiar o link desta simulação</button><span id="msg-copiado" role="status"></span></div>
      </div>
    </section>
  </div>

  <div class="uso" aria-label="Quanto do valor do veículo é entrada e quanto é financiado">
    <div class="uso-t"><span class="t">Valor do veículo</span><b class="v num" id="c-valor">@@D_VALOR@@</b></div>
    <div class="uso-b"><svg class="bar" id="bar-fin" width="100%" height="12" role="img" aria-label="Quanto do valor do veículo é entrada e quanto é financiado">
            <rect width="100%" height="12" rx="6" fill="rgba(255,255,255,.1)"/><rect id="bar-fill" width="@@D_BARRA@@%" height="12" rx="6" fill="#0ea5e9"/><rect id="bar-mark" x="20%" y="-3" width="2" height="18" fill="#e2e8f0"/>
          </svg></div>
    <div class="uso-l">
      <div class="lg"><span><s></s>Financiado (<span id="c-fin-pct">80%</span>)</span><b class="num" id="c-financiado">@@D_FINANCIADO@@</b></div>
      <div class="lg"><span><s class="lim"></s><span id="c-ent-rot">Entrada (20%)</span></span><b class="num" id="c-entrada">@@D_ENTRADA@@</b></div>
    </div>
  </div>

  <div class="kpis" aria-label="Três números para ler o custo">
    <div class="kp"><span class="t">Quita por volta de</span><b class="num" id="k-quita">@@D_K_QUITA@@</b><small id="k-quita-s">@@D_K_QUITA_S@@</small></div>
    <div class="kp"><span class="t">Cada R$ 1 financiado custa</span><b class="num" id="k-juro1">@@D_K_JURO1@@</b><small>de juros até o fim</small></div>
    <div class="kp"><span class="t">Taxa equivalente ao ano</span><b class="num" id="k-aa">@@D_K_AA@@</b><small id="k-aa-s">para comparar com outras taxas</small></div>
  </div>
  <p class="hint kpn" id="k-nota">Estimativa, não é oferta. Taxas dos bancos: Banco Central, semana de @@PERIODO@@.</p>

  <section class="band fatos" aria-label="Taxas dos bancos que acompanhamos">
    <div class="fatos-g">
      <div><b class="num">@@FATO_BANCOS@@</b><span>bancos e financeiras acompanhados</span></div>
      <div><b class="num">@@FATO_MIN@@</b><span>ao mês, a menor taxa média (@@FATO_MIN_NOME@@)</span></div>
      <div><b class="num">@@FATO_MAX@@</b><span>ao mês, a maior taxa média (@@FATO_MAX_NOME@@)</span></div>
      <div><b class="num">R$ 0</b><span>e sem cadastro para simular</span></div>
    </div>
    <p class="hint">Taxa média efetivamente contratada, do Banco Central (modalidade aquisição de veículos, pessoa física). Não é taxa de oferta: a sua depende da análise do banco.</p>
  </section>

  <section class="blk" id="comparar" aria-labelledby="t-cmp">
    <div class="kicker">Comparativo</div>
    <h2 id="t-cmp">O mesmo financiamento, em cada banco</h2>
    <p class="lead" id="cm-lead">@@D_CM_LEAD@@</p>
    <div class="panel cmpx">
      <div class="cmleg"><span><s class="cr"></s>Valor financiado</span><span><s class="jr3"></s>Juros pagos até o fim</span></div>
      <div class="cmrows" id="cm-linhas"></div>
      <div class="cmgap">
        <div class="gv num" id="cm-gap-v">@@D_CM_GAPV@@</div>
        <p id="cm-gap">@@D_CM_GAP@@</p>
      </div>
    </div>
    <div class="hint" id="cm-nota">Mesma entrada e mesmo prazo em todos (limitado ao prazo máximo de cada banco). Taxas médias do Banco Central; a sua proposta pode ser diferente. Veja o <a href="@@LINK_COMPARADOR@@" id="a-comparador">comparador de @@CAT_COMPARADOR@@</a>.</div>
  </section>

  <section class="blk" aria-labelledby="t-raio">
    <div class="raio">
      <div class="hd">
        <div><div class="kicker">Raio-X da decisão</div><h2 id="t-raio">Essa parcela cabe no seu mês?</h2></div>
      </div>
      <div class="mini-in"><label for="campo-conforto">Parcela confortável: quanto cabe por mês?</label><div class="inp"><span class="pre">R$</span><input id="campo-conforto" type="text" inputmode="numeric" autocomplete="off" value="2.000" class="num"><em>/mês</em></div></div>
      <p id="raio-texto">@@D_RAIO@@</p>
      <div class="alts" id="alts"></div>
      <div class="regra" id="regra-renda">
        <div class="rt"><b>E o limite de 30% da renda?</b> <span id="renda-texto">@@D_RENDA@@</span></div>
        <details class="rdet" id="det-renda">
          <summary>Como a renda entra na análise</summary>
          <p>Não existe um percentual único em lei para financiamento de veículo: cada banco define na análise do crédito. A referência de mercado mais citada é a soma das parcelas de dívidas de até cerca de 30% da renda mensal. A conta acima é nossa, não é análise de crédito.</p>
          <p>O banco também olha o histórico de pagamento, o score e o valor da entrada. Uma entrada maior costuma ajudar na aprovação e baixa a parcela.</p>
        </details>
      </div>
      <div class="hint">Não dizemos qual é “melhor”: depende do que importa para você. A parcela confortável é só uma conta sua; não é análise de crédito.</div>
    </div>
  </section>

  <section class="blk amsec" id="amortizacao" aria-labelledby="t-amort">
    <div class="kicker">Amortização</div>
    <h2 id="t-amort">Pagar antes pode poupar milhares de reais</h2>
    <p class="lead amlead">No começo do financiamento, boa parte da parcela é juros. Quando você paga um valor a mais, a dívida em que os juros incidem diminui: você termina antes e paga menos. Veja quanto isso vale no seu cenário.</p>

    <div class="split amwhy">
      <div class="split-t">
        <h3 class="sub"><span class="n" aria-hidden="true">1</span>Os juros vêm primeiro</h3>
        <div class="giga num"><span id="amort-pct">@@D_AMORT_PCT@@%</span><small>do 1º ano é juros</small></div>
        <p class="lead" id="amort-resumo">@@D_AMORT_RESUMO@@</p>
      </div>
      <div class="panel graf">
        <div class="leg">
          <span><s class="jr"></s>Juros do ano</span><span><s></s>Amortização do ano</span><span><s class="ln"></s>Saldo devedor</span>
        </div>
        <svg id="amort-graf" viewBox="0 0 640 220" preserveAspectRatio="none" role="img" aria-label="Gráfico: juros e amortização de cada ano e saldo devedor"></svg>
        <div class="eixo"><span>Ano 1</span><span id="amort-ano-fim">Ano 4</span></div>
      </div>
    </div>

    <details class="amort amsim" id="det-amsim">
      <summary>Simular: pagar a mais todo mês ou amortizar de uma vez</summary>
    <div class="panel amx">
      <h3 class="sub"><span class="n" aria-hidden="true">2</span>Amortização: quanto você poupa pagando a mais</h3>
      <p class="amsub">Escolha o valor e o momento. Quanto mais cedo, maior a economia. A parcela continua a mesma e o prazo encurta.</p>
      <div class="amin">
        <div class="f">
          <label for="campo-extra">Pagar a mais todo mês <span>além da parcela</span></label>
          <div class="inp"><span class="pre">R$</span><input id="campo-extra" type="text" inputmode="numeric" autocomplete="off" value="300" class="num"><em>/mês</em></div>
        </div>
        <div class="f">
          <label for="campo-unico">Amortização única <span>um valor de uma vez</span></label>
          <div class="inp"><span class="pre">R$</span><input id="campo-unico" type="text" inputmode="numeric" autocomplete="off" value="5.000" class="num"></div>
        </div>
        <div class="f">
          <label for="range-quando">Quando fazer a única <span id="quando-rot">daqui a 6 meses</span></label>
          <input id="range-quando" type="range" min="0" max="47" step="1" value="6" aria-describedby="quando-rot">
        </div>
      </div>
      <div class="amcards" id="am-cartoes"></div>
      <p class="qtxt" id="am-texto"></p>
    </div>

    <div class="amdicas">
      <div class="amd"><h4>Prazo ou parcela?</h4><p>Reduzir o prazo costuma poupar mais juros: as últimas parcelas somem. Reduzir a parcela dá folga no orçamento do mês. Pergunte ao banco o que o seu contrato permite.</p></div>
      <div class="amd"><h4>Veja o que o contrato diz</h4><p>O Código de Defesa do Consumidor (art. 52, § 2º) garante a liquidação antecipada com redução proporcional dos juros. Confirme com o banco como pedir, se há tarifa e se o abatimento reduz o prazo ou a parcela. <a href="/aprenda-amortizacao-extra-veiculo">Leia o guia</a>.</p></div>
      <div class="amd"><h4>Compare com outro uso do dinheiro</h4><p>Amortizar equivale a render a taxa da dívida: <b id="am-taxa-aa">@@D_AM_TAXA@@</b> ao ano nesta simulação. Compare com o que o mesmo dinheiro renderia, já descontados impostos, e mantenha uma reserva de emergência. Não é recomendação de investimento.</p></div>
    </div>
    </details>

    <details class="amort" id="det-amort">
      <summary>Ver a amortização ano a ano</summary>
      <div class="tw"><table id="tab-amort">
        <caption id="amort-cap">Parcela fixa (Tabela Price): juros, amortização e saldo devedor no fim de cada ano</caption>
        <thead><tr><th scope="col">Ano</th><th scope="col">Juros</th><th scope="col">Amortização</th><th scope="col">Saldo devedor</th></tr></thead>
        <tbody id="amort-corpo">@@D_AMORT_LINHAS@@</tbody>
        <tfoot id="amort-rodape">@@D_AMORT_TOTAL@@</tfoot>
      </table></div>
      <div class="hint" id="amort-nota">Valores em reais de hoje, sem tarifas nem seguro.</div>
    </details>
  </section>

  <section class="blk" id="taxas" aria-labelledby="t-taxas">
    <div class="kicker">Taxas de hoje</div>
    <h2 id="t-taxas">Taxa de financiamento por banco</h2>
    <p class="lead">Taxa média efetivamente contratada, divulgada pelo Banco Central. O Banco Central não separa carro novo, usado e moto nesta modalidade.</p>
    @@TABELAS_TAXAS@@
  </section>

  <section class="blk" id="categorias" aria-labelledby="t-cat">
    <h2 id="t-cat">Compare por tipo de veículo</h2>
    <div class="cols3">@@CARTOES_CATEGORIA@@</div>
    <p class="hint">Prefere ver a parcela direto? Consulte a <a href="/financiamento-veiculos">tabela de financiamento de veículo por valor e prazo</a> ou veja <a href="/atualizacoes">o que mudou nas taxas esta semana</a>.</p>
  </section>

  <section class="blk" aria-labelledby="t-guias">
    <h2 id="t-guias">Entenda antes de decidir</h2>
    <div class="cols3">@@CARTOES_GUIAS@@</div>
  </section>

  <section class="blk split faqs" aria-labelledby="t-faq">
    <div class="split-t">
      <div class="kicker">Dúvidas</div>
      <h2 id="t-faq">Perguntas frequentes</h2>
    </div>
    <div class="faq">@@FAQ@@</div>
  </section>

  <dialog id="dlg-confirma" aria-labelledby="dlg-titulo">
    <h3 id="dlg-titulo">Antes de continuar</h3>
    <p>Você vai preencher um formulário de um <b>parceiro de crédito</b>, que analisa o seu pedido de financiamento. A página dele mostra o nome da empresa.</p>
    <ul>
      <li>Dados do veículo e do valor que você quer financiar.</li>
      <li>Dados pessoais e de renda, para a análise de crédito.</li>
      <li>O parceiro pode consultar bureaus de crédito, conforme o aviso dele.</li>
      <li>A taxa e o CET finais vêm da proposta do banco e podem ser diferentes desta estimativa.</li>
      <li>Simular aqui não é aprovação e você não é obrigado a contratar.</li>
    </ul>
    <p class="dim">Veja a <a href="https://www.datalabglobal.com/privacidade/">política de privacidade</a> e <a href="/metodologia">como calculamos</a>.</p>
    <div class="row"><a class="btn" id="a-parceiro" href="@@PARCEIRO@@" target="_blank" rel="noopener sponsored">Continuar para o parceiro →</a><button type="button" class="ghost" id="btn-voltar">Voltar e ajustar</button></div>
  </dialog>
"""
