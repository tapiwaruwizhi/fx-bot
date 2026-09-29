import 'package:flutter/material.dart';
import '../models.dart';

class PriceGrid extends StatelessWidget {
  final List<PriceTick> prices;
  const PriceGrid({super.key, required this.prices});

  @override
  Widget build(BuildContext context) {
    if (prices.isEmpty) {
      return const Center(child: Text('No prices yet'));
    }
    return LayoutBuilder(
      builder: (ctx, constraints) {
        final columns = (constraints.maxWidth / 220).floor().clamp(1, 6);
        return GridView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: prices.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            childAspectRatio: 2.2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
          ),
          itemBuilder: (_, i) {
            final p = prices[i];
            final up = p.changePct >= 0;
            final color = up ? const Color(0xFF4CC38A) : const Color(0xFFE05C5C);
            return Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(p.pair, style: Theme.of(ctx).textTheme.titleMedium),
                    Text(
                      p.price.toStringAsFixed(p.pair.endsWith('JPY') ? 3 : 5),
                      style: Theme.of(ctx).textTheme.headlineSmall,
                    ),
                    Row(
                      children: [
                        Icon(up ? Icons.arrow_upward : Icons.arrow_downward,
                            size: 14, color: color),
                        const SizedBox(width: 4),
                        Text(
                          '${p.changePct.toStringAsFixed(2)}%',
                          style: TextStyle(color: color, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }
}
