import { Module, Global } from '@nestjs/common';
import { LoggingService } from './services/logging.service';
import { EncryptionService } from './services/encryption.service';
import { MetricsService } from './services/metrics.service';
import { EmailService } from './services/email.service';

@Global()
@Module({
  providers: [LoggingService, EncryptionService, MetricsService, EmailService],
  exports: [LoggingService, EncryptionService, MetricsService, EmailService],
})
export class CommonModule {}
