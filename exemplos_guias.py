"""
Exemplos calculados para os guias de /aprenda que eram só texto (13/nov/2026).

Por que existe: o Google pergunta se o conteúdo traz "análise original" e "valor substancial em relação às outras
páginas"; o Bing diz que páginas finas perdem elegibilidade. Os números abaixo saem do MESMO cálculo do simulador
(Tabela Price, IOF e CET de gerador_veiculos), então são conferíveis. São hipotéticos: a taxa é um exemplo, não oferta.

montar_exemplos(...) recebe as funções do gerador (evita import circular) e devolve {slug: html}.
"""
TAXA_AM = 1.9  # % ao mês, exemplo
_H2 = '<div class="border-t border-white/10 pt-6">\n            <h2 class="font-serif text-xl text-white mb-3">{t}</h2>\n            {c}\n        </div>'


def _a(href, texto):
    return f'<a href="{href}" class="text-sky-400 underline">{texto}</a>'


def _b(t):
    return f'<strong class="text-white">{t}</strong>'


def _pct(v):
    return f"{v:.2f}".replace(".", ",")


def _price_com_extra(saldo, prazo, taxa_am, mes_extra, extra, modo, pmt_fn):
    """Price com um pagamento extra logo após a parcela `mes_extra`. 'prazo' mantém a parcela e encurta o contrato;
    'parcela' mantém o prazo e reduz a parcela. Devolve (juros_totais, meses, parcela_depois)."""
    i = taxa_am / 100
    pmt = pmt_fn(saldo, prazo, taxa_am)
    juros = 0.0
    for _ in range(mes_extra):
        j = saldo * i
        juros += j
        saldo -= pmt - j
    saldo -= extra
    if modo == "parcela":
        restantes = prazo - mes_extra
        pmt2 = pmt_fn(saldo, restantes, taxa_am)
        for _ in range(restantes):
            j = saldo * i
            juros += j
            saldo -= pmt2 - j
        return juros, prazo, pmt2
    meses = mes_extra
    while saldo > 0.005:
        j = saldo * i
        juros += j
        saldo -= min(pmt - j, saldo)
        meses += 1
    return juros, meses, pmt


def montar_exemplos(pmt_fn, iof_fn, cet_fn, tarifa_registro, reais, renda_fn):
    ex = {}
    ta = ((1 + TAXA_AM / 100) ** 12 - 1) * 100

    # ---- Tabela Price
    v, n = 60_000, 48
    pmt = pmt_fn(v, n, TAXA_AM)
    i = TAXA_AM / 100
    j1 = v * i
    saldo_ult = pmt / (1 + i)
    j_ult = saldo_ult * i
    ex["aprenda-tabela-price"] = _H2.format(t="Exemplo calculado: R$ 60 mil em 48 parcelas", c=(
        f"<p>Um exemplo hipotético, calculado como o simulador calcula: financiar {_b('R$ 60.000')} em {_b('48 meses')} a "
        f"{_b(_pct(TAXA_AM) + '% ao mês')} (cerca de {_pct(ta)}% ao ano). A parcela da Price é {_b(reais(pmt))} do primeiro ao último mês, e você paga "
        f"{reais(pmt * n)} no total, dos quais {_b(reais(pmt * n - v))} são juros.</p>"
        f'<ul class="list-disc pl-6 space-y-2">'
        f"<li>{_b('Na 1ª parcela:')} {reais(j1)} são juros e só {reais(pmt - j1)} abatem a dívida.</li>"
        f"<li>{_b('Na 48ª parcela:')} {reais(j_ult)} são juros e {reais(pmt - j_ult)} abatem a dívida.</li></ul>"
        f"<p>É essa inversão que torna a amortização antecipada mais vantajosa no começo do contrato: nas primeiras parcelas, quase tudo que você paga "
        f"é juros. Veja como funciona em {_a('aprenda-amortizacao-extra-veiculo', 'amortização extra')}.</p>"))

    # ---- Entrada ideal
    preco, prazo = 80_000, 48
    linhas = []
    for pct in (10, 20, 30, 40):
        fin = preco * (100 - pct) / 100
        p = pmt_fn(fin, prazo, TAXA_AM)
        linhas.append(f"<li>{_b(f'Entrada de {pct}%')} ({reais(preco - fin)}): financia {reais(fin)}, parcela de {_b(reais(p))}, "
                      f"juros de {reais(p * prazo - fin)}; renda mensal sugerida de {reais(renda_fn(p))}.</li>")
    ex["aprenda-entrada-ideal-financiamento-veiculo"] = _H2.format(t="Exemplo calculado: carro de R$ 80 mil", c=(
        f"<p>Um exemplo hipotético, calculado como o simulador calcula: carro de {_b('R$ 80.000')} financiado em {_b('48 meses')} a "
        f"{_pct(TAXA_AM)}% ao mês. Cada 10 pontos a mais de entrada reduzem a parcela e os juros:</p>"
        f'<ul class="list-disc pl-6 space-y-2">{"".join(linhas)}</ul>'
        f"<p>A renda sugerida considera uma parcela de até 30% da renda bruta, referência comum entre bancos. Teste o seu valor no "
        f"{_a('comparador-carro-novo', 'comparador')}.</p>"))

    # ---- Amortização extra
    s, n, k, extra = 50_000, 48, 12, 10_000
    pmt = pmt_fn(s, n, TAXA_AM)
    j_base = pmt * n - s
    jp, mp, _ = _price_com_extra(s, n, TAXA_AM, k, extra, "prazo", pmt_fn)
    jq, _, pq = _price_com_extra(s, n, TAXA_AM, k, extra, "parcela", pmt_fn)
    ex["aprenda-amortizacao-extra-veiculo"] = _H2.format(t="Exemplo calculado: R$ 10 mil a mais depois de 1 ano", c=(
        f"<p>Um exemplo hipotético: financiamento de {_b('R$ 50.000')} em {_b('48 meses')} a {_pct(TAXA_AM)}% ao mês, parcela de {reais(pmt)}. "
        f"Sem amortizar, você paga {_b(reais(j_base))} de juros. Depois de pagar a 12ª parcela, você coloca {_b(reais(extra))} a mais:</p>"
        f'<ul class="list-disc pl-6 space-y-2">'
        f"<li>{_b('Reduzindo o prazo:')} a parcela continua {reais(pmt)} e o contrato termina em {_b(f'{mp} meses')} (em vez de 48). Juros: "
        f"{reais(jp)}, economia de {_b(reais(j_base - jp))}.</li>"
        f"<li>{_b('Reduzindo a parcela:')} o prazo continua 48 meses e a parcela cai para {_b(reais(pq))}. Juros: {reais(jq)}, economia de "
        f"{_b(reais(j_base - jq))}.</li></ul>"
        f"<p>Encurtar o prazo economiza mais juros; reduzir a parcela alivia o mês. Pelo Código de Defesa do Consumidor, o abatimento antecipado tem "
        f"direito à redução proporcional dos juros (veja as fontes abaixo); confirme com o banco como ele aplica.</p>"))

    # ---- IOF e CET (mesmo exemplo)
    v, n = 50_000, 48
    pmt = pmt_fn(v, n, TAXA_AM)
    iof = iof_fn(v, n)
    liquido = v - iof - tarifa_registro
    cet = cet_fn(v, n, TAXA_AM)
    ex["aprenda-iof-financiamento-veiculo"] = _H2.format(t="Exemplo calculado: IOF em R$ 50 mil e 48 meses", c=(
        f"<p>Um exemplo hipotético, calculado como o simulador calcula: financiamento de {_b('R$ 50.000')} em {_b('48 meses')}. O IOF é de "
        f"{_b('0,38%')} fixo ({reais(v * 0.0038)}) mais {_b('0,0082% ao dia')} por até 365 dias ({reais(iof - v * 0.0038)}), no total de {_b(reais(iof))}, "
        f"{_pct(100 * iof / v)}% do valor financiado. Como o prazo passa de um ano, a parte diária chega ao teto de 365 dias. As alíquotas são fixadas por decreto e podem mudar: confira a vigente na proposta do banco.</p>"
        f"<p>Esse valor costuma ser descontado do que o banco libera: você recebe menos do que financia, mas paga a parcela sobre o valor cheio. "
        f"Veja o efeito no custo em {_a('aprenda-o-que-e-cet', 'o que é CET')}.</p>"))
    ex["aprenda-o-que-e-cet"] = _H2.format(t="Exemplo calculado: da taxa de juros ao CET", c=(
        f"<p>Um exemplo hipotético, calculado como o simulador calcula: financiamento de {_b('R$ 50.000')} em {_b('48 meses')} com taxa de juros de "
        f"{_b(_pct(TAXA_AM) + '% ao mês')} (cerca de {_pct(ta)}% ao ano). A parcela é de {reais(pmt)}. Só que, do valor financiado, saem o IOF "
        f"({reais(iof)}) e uma tarifa típica de registro do contrato ({reais(tarifa_registro)}): você recebe {_b(reais(liquido))} e paga a parcela "
        f"sobre R$ 50.000. Somando também um seguro prestamista estimado, o CET fica em {_b(_pct(cet) + '% ao ano')}, acima dos {_pct(ta)}% da taxa de juros.</p>"
        f"<p>Por isso a comparação entre propostas deve ser feita pelo CET que consta no contrato, e não pela taxa mensal anunciada. "
        f"Seguro e tarifas variam por banco e por pessoa; aqui são estimativas de mercado.</p>"))

    # ---- CDC: a garantia dura até o saldo zerar
    v, n = 50_000, 48
    pmt = pmt_fn(v, n, TAXA_AM)
    i = TAXA_AM / 100

    def saldo(pagas):
        return pmt * (1 - (1 + i) ** -(n - pagas)) / i

    linhas = "".join(
        f"<li>{_b(f'Depois de {k} parcelas:')} você já pagou {reais(pmt * k)} e o saldo devedor ainda é de {_b(reais(saldo(k)))} "
        f"({_pct(100 * saldo(k) / v)}% do valor financiado).</li>" for k in (12, 24, 36, 47))
    ex["aprenda-o-que-e-cdc"] = _H2.format(t="Exemplo calculado: quanto você ainda deve enquanto o veículo é a garantia", c=(
        f"<p>Um exemplo hipotético, calculado como o simulador calcula: CDC de {_b('R$ 50.000')} em {_b('48 parcelas fixas')} de {_b(reais(pmt))} "
        f"a {_pct(TAXA_AM)}% ao mês (Tabela Price, sem IOF, tarifas e seguro). Enquanto houver saldo devedor, o veículo segue como garantia (alienação fiduciária):</p>"
        f'<ul class="list-disc pl-6 space-y-2">{linhas}</ul>'
        f"<p>Os juros pesam mais no começo, por isso o saldo cai devagar nas primeiras parcelas: na metade do contrato você já pagou "
        f"{reais(pmt * 24)}, mas ainda deve {_pct(100 * saldo(24) / v)}% do valor financiado. A restrição no documento só sai quando o saldo chega a zero. "
        f"Veja como isso muda se você {_a('aprenda-amortizacao-extra-veiculo', 'amortizar antes')} e o que entra no custo no guia {_a('aprenda-o-que-e-cet', 'o que é CET')}.</p>"))

    # ---- Financiamento x consórcio
    carta = 50_000
    juros = pmt * n - carta
    j24 = pmt_fn(carta, 24, TAXA_AM) * 24 - carta
    ex["aprenda-financiamento-x-consorcio-veiculo"] = _H2.format(t="Exemplo calculado: quanto o financiamento cobra de juros em R$ 50 mil", c=(
        f"<p>Um exemplo hipotético, calculado como o simulador calcula (Tabela Price, {_pct(TAXA_AM)}% ao mês, sem IOF, tarifas e seguro). "
        f"Para ter {_b('R$ 50.000')} de crédito, o financiamento cobra:</p>"
        f'<ul class="list-disc pl-6 space-y-2">'
        f"<li>{_b('Em 48 meses:')} parcela de {reais(pmt)} e {_b(reais(juros))} de juros no total, o equivalente a {_b(_pct(100 * juros / carta) + '% do crédito')}.</li>"
        f"<li>{_b('Em 24 meses:')} parcela de {reais(pmt_fn(carta, 24, TAXA_AM))} e {_b(reais(j24))} de juros, ou {_b(_pct(100 * j24 / carta) + '% do crédito')}.</li></ul>"
        f"<p>No consórcio não há juros, mas há a taxa de administração, a correção monetária da carta e da mensalidade, e outros itens que o contrato "
        f"prever (como fundo de reserva e seguro). Esses percentuais variam por administradora e estão no contrato. A comparação justa é: some tudo o que "
        f"o contrato do consórcio cobra, calcule o percentual sobre a carta e compare com os percentuais acima. E lembre que o financiamento entrega o "
        f"veículo no mesmo dia, enquanto no consórcio a data depende de sorteio ou lance. Simule o financiamento no {_a('comparador-carro-novo', 'comparador')}.</p>"))
    return ex
