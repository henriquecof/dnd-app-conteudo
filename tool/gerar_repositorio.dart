// Gera/atualiza o repositorio.json a partir dos pacotes da pasta.
//
// Uso (na raiz do repositório de conteúdo):
//   dart run tool/gerar_repositorio.dart <pasta-do-repo> [--nome "Conteúdo do app"]
//
// Valida cada pacote, calcula sha256 e tamanho, e confere se as dependências
// existem no próprio repositório ou no SRD embutido no app.
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';

const embedded = {'srd-5.1'};
final idPattern = RegExp(r'^[a-z0-9][a-z0-9_.-]*$');

/// Listas de conteúdo de um pacote (para mostrar "N itens" no app).
const contentLists = [
  'racas', 'subracas', 'classes', 'arquetipos', 'magias', 'antecedentes', 'talentos',
  'itens', 'itens_magicos', 'criaturas', 'condicoes', 'aventuras',
];

int _count(Map<String, dynamic> j) =>
    contentLists.fold(0, (n, k) => n + ((j[k] as List?)?.length ?? 0)); // vem dentro do app; não precisa estar no repositório

void main(List<String> args) {
  if (args.isEmpty) {
    stderr.writeln('uso: dart run tool/gerar_repositorio.dart <pasta-do-repo> [--nome "Nome"]');
    exit(64);
  }
  final root = Directory(args.first);
  final nameIdx = args.indexOf('--nome');
  final indexFile = File('${root.path}/repositorio.json');
  final previous = indexFile.existsSync() ? jsonDecode(indexFile.readAsStringSync()) as Map<String, dynamic> : null;
  final name = nameIdx >= 0 && nameIdx + 1 < args.length ? args[nameIdx + 1] : previous?['nome'] ?? 'Conteúdo do app';

  final packsDir = Directory('${root.path}/pacotes');
  final files = packsDir.listSync().whereType<File>().where((f) => f.path.endsWith('.json')).toList()
    ..sort((a, b) => a.path.compareTo(b.path));

  final entries = <Map<String, dynamic>>[];
  final ids = <String>{};
  var failed = false;
  for (final f in files) {
    final bytes = f.readAsBytesSync();
    final Map<String, dynamic> j;
    try {
      j = jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>;
    } catch (e) {
      stderr.writeln('ERRO ${f.path}: JSON inválido ($e)');
      failed = true;
      continue;
    }
    for (final k in ['formato', 'id', 'nome', 'versao']) {
      if (j[k] == null) {
        stderr.writeln('ERRO ${f.path}: falta "$k"');
        failed = true;
      }
    }
    final id = j['id'] is String ? j['id'] as String : '';
    if (!idPattern.hasMatch(id) || id.contains('..')) {
      stderr.writeln('ERRO ${f.path}: id "$id" inválido (minúsculas, dígitos, ".", "_" e "-")');
      failed = true;
    } else if ('$id.json' != f.uri.pathSegments.last) {
      stderr.writeln('ERRO ${f.path}: o arquivo deve se chamar $id.json');
      failed = true;
    }
    if (!ids.add(id)) {
      stderr.writeln('ERRO ${f.path}: id ${j['id']} repetido');
      failed = true;
    }
    entries.add({
      'id': j['id'],
      'nome': j['nome'],
      'versao': j['versao'],
      'descricao': j['descricao'] ?? '',
      'depende_de': j['depende_de'] ?? <String>[],
      if (j['categoria'] != null) 'categoria': j['categoria'],
      if (j['publico'] != null) 'publico': j['publico'],
      if (j['idioma'] != null) 'idioma': j['idioma'],
      if (j['fonte'] != null) 'fonte': j['fonte'],
      if (j['licenca'] != null) 'licenca': j['licenca'],
      'contagem': _count(j),
      'url': 'pacotes/${f.uri.pathSegments.last}',
      'sha256': sha256.convert(bytes).toString(),
      'tamanho': bytes.length,
    });
  }

  for (final e in entries) {
    for (final d in (e['depende_de'] as List).cast<String>()) {
      if (!ids.contains(d) && !embedded.contains(d)) {
        stderr.writeln('ERRO ${e['id']}: depende de "$d", que não está no repositório');
        failed = true;
      }
    }
  }
  // Índices do Aurora com licença aberta que o app sugere (só https).
  final auroraFile = File('${root.path}/fontes_aurora.json');
  final aurora = auroraFile.existsSync() ? (jsonDecode(auroraFile.readAsStringSync()) as List) : const [];
  for (final a in aurora.cast<Map<String, dynamic>>()) {
    if (a['nome'] == null || !(a['url'] as String? ?? '').startsWith('https://') || a['licenca'] == null) {
      stderr.writeln('ERRO fontes_aurora.json: "${a['nome']}" precisa de nome, url https e licenca');
      failed = true;
    }
  }
  if (failed) exit(1);

  final out = {
    'formato': 1,
    'nome': name,
    'atualizado_em': DateTime.now().toUtc().toIso8601String(),
    'pacotes': entries,
    'fontes_aurora': aurora,
  };
  indexFile.writeAsStringSync('${const JsonEncoder.withIndent('  ').convert(out)}\n');
  stdout.writeln('repositorio.json: ${entries.length} pacote(s)');
}
