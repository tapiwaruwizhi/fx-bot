import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'models.dart';

/// Set at build time:  flutter build web --dart-define=API_URL=https://your-api.onrender.com
/// Falls back to the local backend for development.
const String _apiUrl =
    String.fromEnvironment('API_URL', defaultValue: 'http://localhost:8000');

class ApiService {
  final String baseUrl;

  ApiService({String? baseUrl})
      : baseUrl = (baseUrl ?? _apiUrl).replaceAll(RegExp(r'/+$'), '');

  /// http -> ws, https -> wss
  String get wsUrl => '${baseUrl.replaceFirst(RegExp(r'^http'), 'ws')}/ws';

  Future<DashboardSnapshot> fetchSnapshot() async {
    final r = await http.get(Uri.parse('$baseUrl/api/snapshot'));
    if (r.statusCode != 200) {
      throw Exception('snapshot failed: ${r.statusCode}');
    }
    return DashboardSnapshot.fromJson(jsonDecode(r.body));
  }

  /// Stream of typed updates from the backend.
  /// Emits maps like {'type': 'news'|'prices'|'signals'|'calendar'|'snapshot', 'data': ...}
  Stream<Map<String, dynamic>> connect() {
    final channel = WebSocketChannel.connect(Uri.parse(wsUrl));
    return channel.stream
        .map((raw) => jsonDecode(raw as String) as Map<String, dynamic>);
  }
}
