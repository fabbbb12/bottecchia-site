<?php
/**
 * Envio simples do formulário de contato por e-mail (PHP mail()).
 *
 * Funciona "out of the box" na maioria das hospedagens compartilhadas
 * (o mesmo tipo de ambiente que o site já usava antes). Não requer
 * bibliotecas externas nem configuração de API.
 *
 * Caso o e-mail não seja entregue por causa das regras de SPF/DKIM do
 * servidor, recomenda-se trocar por um serviço como SMTP autenticado,
 * Brevo, SendGrid ou Formspree — basta substituir a função enviarEmail()
 * abaixo mantendo o mesmo formato de resposta (HTTP 200 = sucesso).
 */

header('Content-Type: application/json; charset=utf-8');

$destinatario = 'contato@bottecchia.adv.br';

function campo($nome) {
    return isset($_POST[$nome]) ? trim(strip_tags($_POST[$nome])) : '';
}

// Honeypot anti-spam (campo invisível; se vier preenchido, ignora silenciosamente)
if (campo('website') !== '') {
    http_response_code(200);
    echo json_encode(['ok' => true]);
    exit;
}

$nome     = campo('nome');
$email    = campo('email');
$telefone = campo('telefone');
$assunto  = campo('assunto') ?: 'Novo contato pelo site';
$mensagem = campo('mensagem');

if ($_SERVER['REQUEST_METHOD'] !== 'POST' || $nome === '' || $email === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(422);
    echo json_encode(['ok' => false, 'error' => 'Dados inválidos.']);
    exit;
}

$corpo = "Nova mensagem recebida pelo site bottecchia.adv.br\n\n"
       . "Nome: {$nome}\n"
       . "E-mail: {$email}\n"
       . "Telefone: {$telefone}\n"
       . "Assunto: {$assunto}\n\n"
       . "Mensagem:\n{$mensagem}\n";

$headers   = [];
$headers[] = 'From: Site Bottecchia <nao-responda@bottecchia.adv.br>';
$headers[] = 'Reply-To: ' . $nome . ' <' . $email . '>';
$headers[] = 'Content-Type: text/plain; charset=UTF-8';

$enviado = @mail($destinatario, '[Site] ' . $assunto, $corpo, implode("\r\n", $headers));

if ($enviado) {
    http_response_code(200);
    echo json_encode(['ok' => true]);
} else {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Falha ao enviar e-mail no servidor.']);
}
