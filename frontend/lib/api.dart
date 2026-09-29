import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'models.dart';

class ApiService {
  final String baseUrl;
  final String wsUrl;

  ApiService({
    this.baseUrl = 'http://localhost:8000',
    this.wsUrl = 'ws://localhost:8000/ws',
  });

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
    return channel.stream.map((raw) => jsonDecode(raw as String) as Map<String, dynamic>);
  }
}
