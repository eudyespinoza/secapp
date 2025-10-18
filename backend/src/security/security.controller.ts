import { Controller, Get, Post, Put, Query, Param, Body } from '@nestjs/common';
import { SecurityService } from './security.service';

@Controller('security')
export class SecurityController {
  constructor(private readonly securityService: SecurityService) {}

  @Get('audit-logs')
  async getAuditLogs(
    @Query('userId') userId?: string,
    @Query('action') action?: string,
    @Query('resource') resource?: string,
    @Query('severity') severity?: string,
    @Query('suspicious') suspicious?: string,
    @Query('startDate') startDate?: string,
    @Query('endDate') endDate?: string,
    @Query('page') page?: string,
    @Query('limit') limit?: string,
  ) {
    return this.securityService.getAuditLogs({
      userId,
      action,
      resource,
      severity,
      suspicious: suspicious === 'true' ? true : suspicious === 'false' ? false : undefined,
      startDate: startDate ? new Date(startDate) : undefined,
      endDate: endDate ? new Date(endDate) : undefined,
      page: page ? parseInt(page) : undefined,
      limit: limit ? parseInt(limit) : undefined,
    });
  }

  @Get('events')
  async getSecurityEvents(
    @Query('severity') severity?: string,
    @Query('suspicious') suspicious?: string,
    @Query('limit') limit?: string,
  ) {
    return this.securityService.getSecurityEvents({
      severity,
      suspicious: suspicious === 'true',
      limit: limit ? parseInt(limit) : undefined,
    });
  }

  @Get('stats')
  async getStats() {
    return this.securityService.getSecurityStats();
  }

  @Get('user/:userId/activity')
  async getUserActivity(
    @Param('userId') userId: string,
    @Query('limit') limit?: string,
  ) {
    return this.securityService.getUserActivity(
      userId,
      limit ? parseInt(limit) : undefined
    );
  }

  @Post('log')
  async logEvent(@Body() eventData: {
    userId: string;
    action: string;
    resource: string;
    ipAddress?: string;
    userAgent?: string;
    metadata?: any;
    severity?: string;
    suspicious?: boolean;
  }) {
    return this.securityService.logEvent(eventData);
  }

  @Put('flag/:logId')
  async flagSuspicious(@Param('logId') logId: string) {
    return this.securityService.flagSuspicious(logId);
  }
}
