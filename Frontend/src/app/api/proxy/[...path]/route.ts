import { NextRequest, NextResponse } from 'next/server';

// Runtime backend URL - read from environment at runtime, not build time
const getBackendUrl = () => {
  return process.env.BACKEND_URL || 'http://localhost:8000';
};

async function proxyRequest(request: NextRequest, params: { path: string[] }) {
  const backendUrl = getBackendUrl();
  const path = params.path.join('/');
  const url = new URL(request.url);
  const targetUrl = `${backendUrl}/api/${path}${url.search}`;

  console.log(`[Proxy] ${request.method} /api/proxy/${path} -> ${targetUrl}`);

  try {
    // Get request body for non-GET requests
    let body: string | undefined;
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      body = await request.text();
    }

    // Forward the request to the backend
    const response = await fetch(targetUrl, {
      method: request.method,
      headers: {
        'Content-Type': request.headers.get('Content-Type') || 'application/json',
        'Accept': request.headers.get('Accept') || 'application/json',
      },
      body: body,
    });

    // Get the response
    const responseBody = await response.text();
    
    console.log(`[Proxy] Response: ${response.status} ${response.statusText}`);

    // Return the proxied response
    return new NextResponse(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error) {
    console.error(`[Proxy] Error proxying to ${targetUrl}:`, error);
    return NextResponse.json(
      { 
        error: 'Backend unavailable', 
        detail: error instanceof Error ? error.message : 'Unknown error',
        targetUrl 
      },
      { status: 502 }
    );
  }
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

export async function PUT(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

