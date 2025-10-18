import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { ConfigService } from '@nestjs/config';
import compression from 'compression';
import helmet from 'helmet';
import { AppModule } from './app.module';
import { LoggingService } from './common/services/logging.service';
import * as Sentry from '@sentry/node';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    bufferLogs: true,
  });

  const configService = app.get(ConfigService);
  const logger = app.get(LoggingService);

  // Sentry Integration
  if (configService.get('SENTRY_ENABLED')) {
    Sentry.init({
      dsn: configService.get('SENTRY_DSN'),
      environment: configService.get('NODE_ENV'),
      tracesSampleRate: parseFloat(configService.get('SENTRY_TRACES_SAMPLE_RATE')),
    });
  }

  // Security Middleware
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        scriptSrc: ["'self'"],
        imgSrc: ["'self'", 'data:', 'https:'],
      },
    },
    hsts: {
      maxAge: 31536000,
      includeSubDomains: true,
      preload: true,
    },
  }));

  // Compression
  app.use(compression());

  // CORS
  const corsOrigins = configService.get('CORS_ORIGIN')?.split(',') || [
    'http://localhost:3000', 
    'http://localhost:3001',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:3001'
  ];
  app.enableCors({
    origin: corsOrigins,
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Request-ID', 'X-Requested-With', 'x-locale', 'Origin', 'Accept'],
  });

  // Global Validation Pipe
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
      transformOptions: {
        enableImplicitConversion: true,
      },
    }),
  );

  // Swagger Documentation (only in development)
  if (configService.get('ENABLE_SWAGGER') === 'true') {
    const config = new DocumentBuilder()
      .setTitle('SecureApprove API')
      .setDescription('Enterprise-grade passwordless approval system API')
      .setVersion('1.0')
      .addBearerAuth()
      .addTag('Authentication', 'WebAuthn and JWT authentication')
      .addTag('Users', 'User management')
      .addTag('Requests', 'Approval requests')
      .addTag('Security', 'Security audit and monitoring')
      .build();

    const document = SwaggerModule.createDocument(app, config);
    SwaggerModule.setup('api/docs', app, document);
  }

  // Global Prefix
  app.setGlobalPrefix('api');

  // Graceful Shutdown
  app.enableShutdownHooks();

  const port = configService.get('API_PORT') || 3000;
  const instanceId = configService.get('INSTANCE_ID') || 'unknown';

  await app.listen(port);

  logger.log(`🚀 SecureApprove API [${instanceId}] running on port ${port}`, 'Bootstrap');
  logger.log(`📝 Environment: ${configService.get('NODE_ENV')}`, 'Bootstrap');
  
  if (configService.get('ENABLE_SWAGGER') === 'true') {
    logger.log(`📚 Swagger docs available at http://localhost:${port}/api/docs`, 'Bootstrap');
  }
}

bootstrap();
