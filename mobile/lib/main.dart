import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:wifi_iot/wifi_iot.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const RicohApp());
}

class RicohApp extends StatelessWidget {
  const RicohApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Ricoh Downloader',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final _ssidCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _hostCtrl = TextEditingController(text: '192.168.0.1');

  List<String> _history = [];
  bool _isDownloading = false;
  String _statusMessage = 'Pronto para baixar.';
  double _progress = 0;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _ssidCtrl.text = prefs.getString('ssid') ?? '';
      _passCtrl.text = prefs.getString('pass') ?? '';
      _hostCtrl.text = prefs.getString('host') ?? '192.168.0.1';
      _history = prefs.getStringList('history') ?? [];
    });
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('ssid', _ssidCtrl.text.trim());
    await prefs.setString('pass', _passCtrl.text.trim());
    await prefs.setString('host', _hostCtrl.text.trim());
  }

  Future<void> _saveHistory() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('history', _history);
  }

  Future<bool> _requestPermissions() async {
    await [
      Permission.location,
      Permission.storage,
      Permission.manageExternalStorage,
      Permission.nearbyWifiDevices,
    ].request();
    return true;
  }

  Future<void> _startDownload() async {
    if (_isDownloading) return;
    FocusScope.of(context).unfocus();
    await _saveSettings();

    setState(() {
      _isDownloading = true;
      _statusMessage = 'Solicitando permissões...';
      _progress = 0;
    });

    await _requestPermissions();

    final ssid = _ssidCtrl.text.trim();
    final pass = _passCtrl.text.trim();
    final host = _hostCtrl.text.trim();

    if (ssid.isNotEmpty && pass.isNotEmpty) {
      setState(() {
        _statusMessage = 'Conectando ao Wi-Fi $ssid...';
      });
      try {
        final connected = await WiFiForIoTPlugin.connect(
          ssid,
          password: pass,
          joinOnce: true,
          security: NetworkSecurity.WPA,
          withInternet: false,
        );
        if (!connected) {
          setState(() {
            _statusMessage = 'Falha ao conectar no Wi-Fi. Certifique-se que a câmera está ligada e o celular não recusou a rede sem internet.';
            _isDownloading = false;
          });
          return;
        }
        await Future.delayed(const Duration(seconds: 4));
      } catch (e) {
        setState(() {
          _statusMessage = 'Erro de Wi-Fi: $e';
          _isDownloading = false;
        });
        return;
      }
    }

    setState(() {
      _statusMessage = 'Buscando lista de fotos em http://$host...';
    });

    List<dynamic> dirs = [];
    try {
      final res = await http.get(Uri.parse('http://$host/v1/photos')).timeout(const Duration(seconds: 15));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        dirs = data['dirs'] ?? [];
      } else {
        throw Exception('Status HTTP ${res.statusCode}');
      }
    } catch (e) {
      setState(() {
        _statusMessage = 'Erro ao contatar a câmera em $host: $e\nSe o Wi-Fi automático falhar, conecte manualmente e tente de novo com SSID em branco.';
        _isDownloading = false;
      });
      return;
    }

    List<Map<String, String>> pendingPhotos = [];
    for (var d in dirs) {
      final dirname = d['name'] ?? '';
      final files = d['files'] ?? [];
      for (var f in files) {
        final filename = f.toString();
        final key = '$dirname/$filename';
        if (!_history.contains(key)) {
          pendingPhotos.add({'dir': dirname, 'file': filename});
        }
      }
    }

    if (pendingPhotos.isEmpty) {
      setState(() {
        _statusMessage = 'Nenhuma foto nova para baixar.';
        _isDownloading = false;
      });
      return;
    }

    setState(() {
      _statusMessage = 'Baixando ${pendingPhotos.length} fotos novas...';
    });

    final baseDir = Directory('/storage/emulated/0/Pictures/Ricoh');
    if (!await baseDir.exists()) {
      try {
        await baseDir.create(recursive: true);
      } catch (e) {
        setState(() {
          _statusMessage = 'Erro ao criar pasta: $e. Verifique a permissão Manage External Storage.';
          _isDownloading = false;
        });
        return;
      }
    }

    int downloadedCount = 0;
    int failedCount = 0;

    for (int i = 0; i < pendingPhotos.length; i++) {
      if (!mounted) break;
      final item = pendingPhotos[i];
      final dirname = item['dir']!;
      final filename = item['file']!;
      final key = '$dirname/$filename';
      
      setState(() {
        _statusMessage = 'Baixando $filename (${i + 1}/${pendingPhotos.length})...';
        _progress = i / pendingPhotos.length;
      });

      try {
        final targetDir = Directory('${baseDir.path}/$dirname');
        if (!await targetDir.exists()) {
          await targetDir.create(recursive: true);
        }

        final fileUrl = 'http://$host/v1/photos/$dirname/$filename';
        final request = http.Request('GET', Uri.parse(fileUrl));
        final response = await request.send().timeout(const Duration(seconds: 120));

        if (response.statusCode == 200) {
          final file = File('${targetDir.path}/$filename');
          final sink = file.openWrite();
          await response.stream.pipe(sink);
          await sink.close();

          _history.add(key);
          downloadedCount++;
        } else {
          failedCount++;
        }
      } catch (e) {
        failedCount++;
      }
    }

    await _saveHistory();

    if (ssid.isNotEmpty && pass.isNotEmpty) {
      try {
        await WiFiForIoTPlugin.disconnect();
      } catch (_) {}
    }

    if (mounted) {
      setState(() {
        _progress = 1.0;
        _isDownloading = false;
        _statusMessage = 'Pronto! Baixadas: $downloadedCount. Falhas: $failedCount.\nSalvas em Pictures/Ricoh';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Ricoh Downloader'),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_sweep),
            tooltip: 'Limpar Histórico',
            onPressed: () async {
              final prefs = await SharedPreferences.getInstance();
              await prefs.remove('history');
              setState(() {
                _history.clear();
                _statusMessage = 'Histórico limpo. Baixará tudo de novo.';
              });
            },
          )
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Se a conexão automática falhar, deixe SSID e Senha em branco, conecte manualmente no celular e tente de novo.', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[700])),
            const SizedBox(height: 16),
            TextField(
              controller: _ssidCtrl,
              decoration: const InputDecoration(
                labelText: 'SSID da Câmera (ex: RICOH_123456)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _passCtrl,
              decoration: const InputDecoration(
                labelText: 'Senha do Wi-Fi',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _hostCtrl,
              decoration: const InputDecoration(
                labelText: 'IP da Câmera (padrão: 192.168.0.1)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _isDownloading ? null : _startDownload,
              icon: const Icon(Icons.download),
              label: const Text('Sincronizar Fotos'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.all(16),
                backgroundColor: Theme.of(context).colorScheme.primaryContainer,
              ),
            ),
            const SizedBox(height: 24),
            if (_isDownloading) ...[
              LinearProgressIndicator(value: _progress > 0 ? _progress : null),
              const SizedBox(height: 16),
            ],
            Text(_statusMessage, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold), textAlign: TextAlign.center),
            const SizedBox(height: 32),
            Text('Fotos no histórico local: ${_history.length}', textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}
