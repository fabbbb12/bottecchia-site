# Site — Bottecchia Advogados Associados

Site institucional novo, estático (HTML + CSS + JavaScript puro, sem frameworks
pesados nem passo de build), pensado para ser rápido, responsivo e fácil de manter.

## Estrutura de pastas

```
index.html              Página única (Início, Sobre, Áreas de Atuação, Instagram, Contato)
css/style.css           Todo o estilo do site (design system em variáveis CSS)
js/main.js              Menu, animações, formulário, WhatsApp, etc.
js/instagram.js         Motor que renderiza as publicações do Instagram
js/instagram-posts.js   ⭐ Onde você cola os links das publicações do Instagram
scripts/contact.php     Recebe o formulário de contato e envia por e-mail
assets/img/             Logos, ícones e imagem de compartilhamento (redes sociais)
favicon.ico             Ícone da aba do navegador
site.webmanifest        Ícones para "adicionar à tela inicial" no celular
robots.txt / sitemap.xml   Arquivos de SEO para o Google
```

## Como colocar publicações reais do Instagram no site

Não é necessário criar um app na Meta nem gerar token de API. Basta:

1. Abrir o Instagram no perfil **@bottecchiaadvogados**.
2. Abrir a publicação (foto, carrossel ou reels) que você quer destacar.
3. Tocar em **"..."** → **"Copiar link"**.
4. Abrir o arquivo `js/instagram-posts.js` e colar o link na lista, um por linha.
5. Salvar o arquivo e publicar o site.

O conteúdo (imagem, legenda, curtidas) é carregado ao vivo direto do Instagram
através do embed oficial do Meta — sempre que a publicação continuar pública,
ela aparece atualizada sozinha. Recomenda-se usar de 3 a 6 publicações.

Enquanto nenhum link for adicionado, a seção mostra automaticamente um convite
elegante para seguir o perfil, então o site nunca fica com um espaço "quebrado".

## Como editar textos e áreas de atuação

Todo o conteúdo de texto está diretamente no `index.html`, organizado em seções
comentadas (`<!-- ============ HISTÓRIA ============ -->` etc.). Basta abrir o
arquivo em qualquer editor e alterar o texto entre as tags `<h2>`, `<p>` etc.
Para adicionar uma nova área de atuação, copie um bloco `.spec-card` inteiro
dentro de `#specGrid` e ajuste o ícone, o título e o texto.

## Formulário de contato

O formulário envia os dados para `scripts/contact.php`, que dispara um e-mail
para `contato@bottecchia.adv.br` usando a função nativa `mail()` do PHP — o
mesmo tipo de recurso que a maioria das hospedagens compartilhadas (como a que
o site já usa) oferece prontamente, sem custo adicional.

Se, ao publicar, o e-mail não chegar (algumas hospedagens bloqueiam `mail()`
por padrão antifraude), duas alternativas simples:

- Peça à hospedagem para habilitar `mail()` ou fornecer um SMTP autenticado.
- Troque por um serviço gratuito como Formspree, Web3Forms ou Brevo: basta
  criar uma conta, colocar a nova URL no atributo `action` do `<form>` em
  `index.html` (seção `#contato`) e remover/manter o `scripts/contact.php`
  conforme a documentação do serviço escolhido.

Como proteção simples contra spam automatizado, existe um campo invisível
("honeypot") chamado `website` — não remova esse campo do HTML.

## Publicando o site (deploy)

Como o site é 100% estático, basta enviar todos os arquivos desta pasta via
FTP/SFTP (ou pelo painel da hospedagem) para a raiz do domínio
`bottecchia.adv.br`, mantendo a mesma estrutura de pastas. Nenhuma instalação,
banco de dados ou build é necessária.

Checklist antes de publicar:

- [ ] Adicionar de 3 a 6 links de publicações em `js/instagram-posts.js`
- [ ] Confirmar telefone, WhatsApp, e-mail e endereço em `index.html`
- [ ] Testar o envio do formulário de contato após subir para o servidor
- [ ] Enviar `sitemap.xml` ao Google Search Console

## SEO e compartilhamento

- Meta description, palavras-chave, Open Graph e dados estruturados
  (`schema.org/LegalService`) já configurados em `index.html`.
- Imagem de compartilhamento (`assets/img/og-image.jpg`) usada no WhatsApp,
  Facebook e Instagram ao colar o link do site.
- `robots.txt` e `sitemap.xml` prontos para indexação no Google.

## Performance e acessibilidade

- Sem jQuery/Bootstrap — apenas CSS e JS nativos, carregamento muito mais
  rápido que o site anterior.
- Layout 100% responsivo (celular, tablet e desktop).
- Botão flutuante de WhatsApp e "voltar ao topo".
- Menu com estado ativo conforme a rolagem, animações suaves ao aparecer o
  conteúdo, formulário acessível por teclado e leitor de tela.
