### Automatizar a comunicação (React ➔ Django) 
Em vez de baixar um ZIP e fazer upload manual, você pode fazer o React enviar os dados diretamente para o Django via código. Isso elimina o processo manual e mantém a segurança.

Como funcionaria o fluxo automatizado:
Você termina a revisão no React.

Em vez de um botão "Baixar ZIP", você terá um botão "Publicar na API".

O React faz um fetch ou usa o axios para enviar o JSON e as imagens para uma rota específica da sua API Django.

O Django recebe tudo, salva no banco e responde "Sucesso!".

### Como estruturar isso no seu TCC?
Se você implementar essa conexão automática, você terá um argumento de peso para a banca: Integração de Sistemas via Web Services.

Você pode descrever assim:

Frontend de Curadoria (React): Consome a API do Google Gemini para extração e fornece interface de edição. Após validação, atua como um client que alimenta o sistema central.

Backend Core (Django): Funciona como um REST Provider, recebendo dados do extrator e servindo dados para o app mobile.

### O que você precisa fazer no código:
No Django: Crie um endpoint (uma rota) que aceite um POST contendo o JSON da questão e os arquivos de imagem.

No React: Use o FormData do JavaScript para agrupar o JSON e as imagens e envie para o endereço da sua API Django.


### App react mais simples!
Deixar o app mais simples