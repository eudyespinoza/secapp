import { Injectable } from '@nestjs/common';

@Injectable()
export class MetricsService {
  constructor() {}

  incrementHttpRequests(method: string, route: string, status: number) {
    // TODO: Implement with prom-client when needed
  }

  observeHttpDuration(method: string, route: string, status: number, duration: number) {
    // TODO: Implement with prom-client when needed
  }

  incrementAuthAttempts(method: string, success: boolean) {
    // TODO: Implement with prom-client when needed
  }

  incrementApprovalMetric(action: string, status: string) {
    // TODO: Implement with prom-client when needed
  }

  async getMetrics(): Promise<string> {
    return 'Metrics service not yet configured';
  }
}
